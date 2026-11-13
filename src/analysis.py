"""可复现的预设分析：本文件不做搜索、调参或结果导向的样本删除。"""
from __future__ import annotations

import hashlib
import json
import platform
import time
import warnings
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.base import clone
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score, confusion_matrix,
                             f1_score, roc_auc_score, roc_curve)
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.multitest import multipletests

from .vendor.assumption_checks import comprehensive_assumption_check

BASE_FEATURES = ['radius', 'texture', 'perimeter', 'area', 'smoothness',
                 'compactness', 'concavity', 'concave_points', 'symmetry',
                 'fractal_dimension']
FEATURES = [prefix + name for prefix in ['mean_', 'se_', 'worst_'] for name in BASE_FEATURES]
MODEL_NAMES = {'DUMMY': 'Prior-only baseline', 'LR30': 'Logistic regression: 30 features',
               'LR10': 'Logistic regression: 10 selected features',
               'LR5': 'Logistic regression: 5 selected features',
               'RF30': 'Random forest: 30 features'}


def utc_now():
    """使用 UTC 记录运行先后顺序，不把系统时区当作课程截止时区。"""
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def clean_json(value):
    """把 NumPy / pandas 结果变成标准 JSON；未定义指标用 null，不写 NaN。"""
    if isinstance(value, pd.DataFrame):
        return clean_json(value.to_dict(orient='records'))
    if isinstance(value, pd.Series):
        return clean_json(value.to_dict())
    if isinstance(value, np.ndarray):
        return clean_json(value.tolist())
    if isinstance(value, dict):
        return {str(k): clean_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_json(v) for v in value]
    if isinstance(value, np.generic):
        return clean_json(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if isinstance(value, Path):
        return str(value)
    return value


def write_json(path, value):
    """临时文件写完再替换，避免网页构建读到半截 JSON。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(clean_json(value), ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    tmp.replace(path)


def save_table(root, name, rows):
    frame = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
    frame.to_csv(root / 'outputs/tables' / name, index=False, encoding='utf-8-sig')


def describe(values):
    a = np.asarray(values, dtype=float)
    return dict(n=len(a), mean=float(a.mean()), sd=float(a.std(ddof=1)),
                median=float(np.median(a)), q1=float(np.quantile(a, .25)),
                q3=float(np.quantile(a, .75)))


def assess_groups(dev, cfg, root):
    """三项预设变量只在开发集分析；M 为 U 检验第一组，效应正值代表 M 偏高。"""
    results, flat_rows, diagnostics = [], [], {}
    rng = np.random.default_rng(cfg['statistics_bootstrap_seed'])
    for feature in cfg['descriptive_features']:
        # 数值屏查不能证实独立性，也不根据其 p 值改变预设 MWU。
        diagnostics[feature] = comprehensive_assumption_check(
            dev, value_col=feature, group_col='diagnosis', plot=False)
        m = dev.loc[dev.target == 1, feature].to_numpy()
        b = dev.loc[dev.target == 0, feature].to_numpy()
        test = stats.mannwhitneyu(m, b, alternative='two-sided', method='asymptotic', use_continuity=True)
        effect = float(2 * test.statistic / (len(m) * len(b)) - 1)
        boot = []
        for _ in range(cfg['bootstrap_repeats']):
            bm = rng.choice(m, size=len(m), replace=True)
            bb = rng.choice(b, size=len(b), replace=True)
            u = stats.mannwhitneyu(bm, bb, alternative='two-sided', method='asymptotic').statistic
            boot.append(2 * u / (len(m) * len(b)) - 1)
        low, high = np.quantile(boot, [.025, .975])
        row = dict(feature=feature, benign=describe(b), malignant=describe(m),
                   u_malignant=float(test.statistic), p_raw=float(test.pvalue),
                   rank_biserial=effect, rank_biserial_ci_low=float(low),
                   rank_biserial_ci_high=float(high))
        results.append(row)
    adjusted = multipletests([r['p_raw'] for r in results], method='holm')[1]
    for row, p in zip(results, adjusted):
        row['p_holm'] = float(p)
        flat = {k: v for k, v in row.items() if k not in ['benign', 'malignant']}
        for group in ['benign', 'malignant']:
            flat.update({group + '_' + k: v for k, v in row[group].items()})
        flat_rows.append(flat)
    save_table(root, 'group_comparisons.csv', flat_rows)
    write_json(root / 'outputs/diagnostics.json', diagnostics)
    return results, diagnostics


def create_models(cfg):
    """Pipeline 交给每折 fit，确保筛选和标准化只看该折训练部分。"""
    models = {'DUMMY': DummyClassifier(strategy='prior')}
    for k in [30, 10, 5]:
        models[f'LR{k}'] = Pipeline([
            ('scaler', StandardScaler()),
            ('selector', SelectKBest(f_classif, k='all' if k == 30 else k)),
            ('classifier', LogisticRegression(**cfg['logistic_regression']))
        ])
    models['RF30'] = RandomForestClassifier(**cfg['random_forest'])
    return models


def selected_names(model, model_id):
    if model_id.startswith('LR'):
        return np.array(FEATURES)[model.named_steps['selector'].get_support()].tolist()
    return [] if model_id == 'DUMMY' else list(FEATURES)


def positive_probability(model, X):
    """显式查找正类 1，避免把另一个数据加载器的编码带进来。"""
    classes = list(model.classes_)
    assert classes == [0, 1], classes
    result = model.predict_proba(X)[:, classes.index(1)]
    assert np.isfinite(result).all() and (result >= 0).all() and (result <= 1).all()
    return result


def evaluate(y, probability, threshold):
    """标签按 [0,1] 排序，混淆矩阵为 [[TN,FP],[FN,TP]]。"""
    prediction = (np.asarray(probability) >= threshold).astype(int)
    tn, fp, fn, tp = [int(n) for n in confusion_matrix(y, prediction, labels=[0, 1]).ravel()]
    return dict(auc=float(roc_auc_score(y, probability)),
                ap=float(average_precision_score(y, probability)),
                sensitivity=tp / (tp + fn), specificity=tn / (tn + fp),
                precision=tp / (tp + fp) if (tp + fp) else None,
                f1=float(f1_score(y, prediction, zero_division=0)),
                accuracy=float(accuracy_score(y, prediction)),
                tn=tn, fp=fp, fn=fn, tp=tp, threshold=threshold)


def fit_checked(model, X, y):
    """收敛警告作为需要处理的问题，不静默忽略。"""
    with warnings.catch_warnings():
        warnings.simplefilter('error', ConvergenceWarning)
        model.fit(X, y)
    return model


def run(root):
    """顺序执行预设流程。最后一次性生成供报告、网页读取的真实结果。"""
    start = time.perf_counter()
    root = Path(root)
    cfg = json.loads((root / 'config.json').read_text(encoding='utf-8'))
    for folder in ['outputs/tables', 'outputs/figures', 'outputs/predictions', 'outputs/models', 'data/processed']:
        (root / folder).mkdir(parents=True, exist_ok=True)
    started_at = utc_now()
    raw_path = root / cfg['source_csv']
    raw_hash = sha256(raw_path)
    config_hash = sha256(root / 'config.json')
    write_json(root / 'outputs/run_started.json', {'started_at_utc': started_at, 'config_sha256': config_hash,
                'source_sha256': raw_hash, 'note': 'All model specifications frozen before fitting.'})
    versions = {name: metadata.version(name) for name in [
        'numpy', 'pandas', 'scipy', 'scikit-learn', 'statsmodels', 'matplotlib', 'seaborn', 'joblib', 'pillow']}
    (root / 'requirements.txt').write_text('\n'.join(f'{k}=={v}' for k, v in versions.items()) + '\n', encoding='utf-8')

    # 读取无表头 CSV；ID 始终作为字符串，不进入 X。
    raw = pd.read_csv(raw_path, header=None, dtype={0: str, 1: str})
    assert raw.shape == (569, 32), raw.shape
    raw.columns = ['id', 'diagnosis'] + FEATURES
    assert set(raw.diagnosis.unique()) == {'B', 'M'}
    raw['target'] = raw.diagnosis.map(cfg['label_mapping']).astype(int)
    X = raw[FEATURES].apply(pd.to_numeric, errors='raise')
    quality = dict(rows=len(raw), input_features=len(FEATURES),
                   missing_feature_values=int(X.isna().sum().sum()),
                   nonfinite_feature_values=int((~np.isfinite(X.to_numpy())).sum()),
                   duplicate_ids=int(raw.id.duplicated().sum()),
                   duplicate_feature_rows=int(X.duplicated().sum()),
                   duplicate_full_rows=int(raw.duplicated().sum()),
                   unknown_labels=int(raw.target.isna().sum()),
                   excluded_rows=0, constant_features=X.columns[X.nunique() <= 1].tolist(),
                   id_excluded_from_predictors=True)
    assert quality['missing_feature_values'] == quality['nonfinite_feature_values'] == quality['duplicate_ids'] == 0
    assert not quality['constant_features']
    write_json(root / 'outputs/quality.json', quality)
    raw.to_csv(root / 'data/processed/wdbc_labeled.csv', index=False, encoding='utf-8-sig')
    all_idx = np.arange(len(raw))
    dev_idx, test_idx = train_test_split(all_idx, test_size=cfg['test_size'], random_state=cfg['split_seed'], stratify=raw.target)
    assert len(set(dev_idx) & set(test_idx)) == 0
    assert set(dev_idx) | set(test_idx) == set(all_idx)
    assignment = pd.DataFrame({'row_index': all_idx, 'id': raw.id, 'target': raw.target,
                               'partition': np.where(np.isin(all_idx, dev_idx), 'development', 'test')})
    assignment.to_csv(root / 'data/processed/split_assignments.csv', index=False, encoding='utf-8-sig')
    dev, test = raw.iloc[dev_idx].copy(), raw.iloc[test_idx].copy()
    X_dev, y_dev, X_test, y_test = dev[FEATURES], dev.target, test[FEATURES], test.target
    split = {name: {'n': len(frame), 'benign': int((frame.target == 0).sum()),
                    'malignant': int((frame.target == 1).sum())}
             for name, frame in [('development', dev), ('test', test)]}
    save_table(root, 'sample_counts.csv', [dict(partition=k, **v) for k, v in split.items()])
    print('[1/6] Data checked and split:', split, flush=True)

    # 先完成开发集统计，不读取测试结果来选择变量。
    statistical_results, diagnostics = assess_groups(dev, cfg, root)
    correlations = X_dev.corr(method='spearman')
    correlations.to_csv(root / 'outputs/tables/spearman_correlations.csv', encoding='utf-8-sig')
    print('[2/6] Development statistics and diagnostic screens completed.', flush=True)

    models = create_models(cfg)
    cv = StratifiedKFold(n_splits=cfg['cv_folds'], shuffle=True, random_state=cfg['cv_seed'])
    folds = list(cv.split(X_dev, y_dev))  # 固定一次，全部模型复用。
    fold_assignments = []
    for fold, (fit_idx, val_idx) in enumerate(folds, 1):
        assert not (set(fit_idx) & set(val_idx))
        assert set(dev_idx[val_idx]).isdisjoint(test_idx)
        for local_idx in val_idx:
            fold_assignments.append({'fold': fold, 'row_index': int(dev_idx[local_idx]),
                                     'id': dev.iloc[local_idx].id, 'target': int(y_dev.iloc[local_idx])})
    save_table(root, 'cv_fold_assignments.csv', fold_assignments)
    cv_rows, selected_rows, cv_results = [], [], {}
    for model_id, estimator in models.items():
        scores, selections = [], []
        for fold, (fit_idx, val_idx) in enumerate(folds, 1):
            model = fit_checked(clone(estimator), X_dev.iloc[fit_idx], y_dev.iloc[fit_idx])
            probability = positive_probability(model, X_dev.iloc[val_idx])
            metrics = evaluate(y_dev.iloc[val_idx], probability, cfg['threshold'])
            scores.append(metrics['auc'])
            cv_rows.append(dict(model=model_id, fold=fold, train_n=len(fit_idx), validation_n=len(val_idx), **metrics))
            names = selected_names(model, model_id)
            selections.append(names)
            selected_rows.extend(dict(model=model_id, fold=fold, feature=feature) for feature in names)
            # 检查 scaler 实际仅拟合该折训练子集。
            if model_id.startswith('LR'):
                assert np.allclose(model.named_steps['scaler'].mean_, X_dev.iloc[fit_idx].mean().to_numpy())
                assert model.named_steps['scaler'].n_samples_seen_ == len(fit_idx)
                assert len(names) == int(model_id[2:])
        cv_results[model_id] = dict(mean_auc=float(np.mean(scores)), sd_auc=float(np.std(scores, ddof=1)),
                                     fold_auc=scores, selections=selections)
    save_table(root, 'cv_fold_metrics.csv', cv_rows)
    save_table(root, 'cv_selected_features.csv', selected_rows)
    candidate_order = sorted(cfg['default_candidates'], key=lambda m: (-cv_results[m]['mean_auc'], int(m[2:])))
    default_model = candidate_order[0]
    frozen_at = utc_now()
    # 此文件写出之后才首次计算最终测试预测，提供顺序上的可审计证据。
    frozen = dict(frozen_at_utc=frozen_at, config_sha256=config_hash,
                  source_sha256=raw_hash, selection_rule=cfg['default_selection_rule'],
                  default_candidates=cfg['default_candidates'], default_model=default_model,
                  cv_results={m: {k: v for k, v in result.items() if k != 'selections'} for m, result in cv_results.items()},
                  threshold=cfg['threshold'], test_predictions_not_yet_computed=True)
    write_json(root / 'outputs/frozen_selection.json', frozen)
    print('[3/6] CV completed; default model frozen before test:', default_model, flush=True)

    model_results, probability_by_model, final_coefficients, final_features, frequency_rows = {}, {}, [], [], []
    all_predictions = pd.DataFrame({'row_index': test_idx, 'id': test.id.to_numpy(), 'true_label': y_test.to_numpy()})
    fit_start = utc_now()
    for model_id, estimator in models.items():
        fitted = fit_checked(clone(estimator), X_dev, y_dev)
        probability = positive_probability(fitted, X_test)
        probability_by_model[model_id] = probability
        metrics = evaluate(y_test, probability, cfg['threshold'])
        names = selected_names(fitted, model_id)
        selected = cv_results[model_id]['selections']
        frequencies = [{'feature': feature, 'count': sum(feature in f for f in selected)} for feature in FEATURES]
        frequencies.sort(key=lambda r: (-r['count'], r['feature']))
        coefficients = []
        if model_id.startswith('LR'):
            coefficients = [{'feature': feature, 'coefficient': float(coef)} for feature, coef in
                            zip(names, fitted.named_steps['classifier'].coef_[0])]
            final_coefficients.extend(dict(model=model_id, **row) for row in coefficients)
            assert fitted.named_steps['scaler'].n_samples_seen_ == len(dev)
        final_features.extend(dict(model=model_id, feature=feature) for feature in names)
        frequency_rows.extend(dict(model=model_id, **row) for row in frequencies)
        fpr, tpr, _ = roc_curve(y_test, probability)
        model_results[model_id] = dict(name=MODEL_NAMES[model_id], k=len(names),
             cv={k: v for k, v in cv_results[model_id].items() if k != 'selections'},
             test=metrics, features=names, coefficients=coefficients,
             feature_selection_frequency=frequencies, roc={'fpr': fpr.tolist(), 'tpr': tpr.tolist()},
             figures={'confusion_png': f'figures/confusion_{model_id}.png'})
        all_predictions[model_id + '_probability'] = probability
        all_predictions[model_id + '_prediction'] = (probability >= cfg['threshold']).astype(int)
        joblib.dump(fitted, root / f'outputs/models/{model_id}.joblib')
    all_predictions.to_csv(root / 'outputs/predictions/test_predictions.csv', index=False, encoding='utf-8-sig')
    save_table(root, 'final_selected_features.csv', final_features)
    save_table(root, 'logistic_coefficients.csv', final_coefficients)
    save_table(root, 'feature_selection_frequency.csv', frequency_rows)
    print('[4/6] Prespecified final models fitted and test predictions saved.', flush=True)

    # 对同一抽样病例比较所有模型，保持预测差值的配对结构。
    rng = np.random.default_rng(cfg['test_bootstrap_seed'])
    y_array = y_test.to_numpy()
    negative_idx, positive_idx = np.flatnonzero(y_array == 0), np.flatnonzero(y_array == 1)
    boot_auc = {model_id: [] for model_id in models}
    for _ in range(cfg['bootstrap_repeats']):
        sample_idx = np.r_[rng.choice(negative_idx, len(negative_idx), replace=True),
                           rng.choice(positive_idx, len(positive_idx), replace=True)]
        for model_id, probability in probability_by_model.items():
            boot_auc[model_id].append(float(roc_auc_score(y_array[sample_idx], probability[sample_idx])))
    for model_id, values in boot_auc.items():
        low, high = np.quantile(values, [.025, .975])
        model_results[model_id]['test'].update(auc_ci_low=float(low), auc_ci_high=float(high))
    comparisons = []
    for model_id in ['LR5', 'LR10']:
        difference = np.asarray(boot_auc[model_id]) - np.asarray(boot_auc['LR30'])
        low, high = np.quantile(difference, [.025, .975])
        comparisons.append(dict(contrast=model_id + '-LR30',
             estimate=model_results[model_id]['test']['auc'] - model_results['LR30']['test']['auc'],
             ci_low=float(low), ci_high=float(high)))
    boot_frame = pd.DataFrame(boot_auc)
    boot_frame.insert(0, 'bootstrap_iteration', np.arange(1, len(boot_frame) + 1))
    save_table(root, 'test_bootstrap_auc.csv', boot_frame)
    save_table(root, 'auc_comparisons.csv', comparisons)
    save_table(root, 'model_test_metrics.csv', [dict(model=m, k=r['k'], **r['test']) for m, r in model_results.items()])
    save_table(root, 'model_cv_summary.csv', [dict(model=m, k=r['k'], mean_auc=r['cv']['mean_auc'], sd_auc=r['cv']['sd_auc']) for m, r in model_results.items()])

    summary = dict(schema_version='1.0', title=cfg['project_title'], status='executed', generated_at_utc=utc_now(),
        source=dict(file=cfg['source_csv'], description_file=cfg['source_description'], rows=len(raw), features=len(FEATURES),
                    label_counts={'B': int((raw.target == 0).sum()), 'M': int((raw.target == 1).sum())},
                    sha256=raw_hash, url='https://archive.ics.uci.edu/dataset/17/breast+cancer+wisconsin+diagnostic'),
        split=split, quality=quality, versions=versions,
        methods={**cfg, 'confidence_interval': '95% percentile bootstrap',
                 'statistics_bootstrap': 'Independent within-diagnosis resampling; malignant first for U and signed rank-biserial effect.',
                 'test_bootstrap': 'Stratified by true class; identical resampling indices for all models; fixed-model conditional uncertainty.',
                 'mwu': 'Two-sided asymptotic Mann–Whitney U with continuity and tie correction; Holm correction across 3 planned comparisons.',
                 'diagnostics': 'Groupwise Shapiro-Wilk, median-centered Levene and 1.5-IQR screens; no exclusions or test switching.',
                 'independence': 'Analysis treats records as independent; unique IDs do not establish broader sampling independence.'},
        statistics={'features': statistical_results, 'diagnostics_file': 'diagnostics.json'},
        models=model_results, comparisons=comparisons, default_model=default_model,
        figures={key + '_png': 'figures/' + value + '.png' for key, value in [
            ('descriptives', 'feature_distributions'), ('correlation', 'spearman_heatmap'),
            ('performance', 'model_performance'), ('roc', 'test_roc'), ('selection', 'selection_frequency'),
            ('coefficients', 'logistic_coefficients'), ('bootstrap', 'auc_differences')]},
        limitations=[
            '单一历史公开数据集的内部验证，不代表外部医院或现实筛查人群的表现。',
            '特征来自同类穿刺图像；减少模型输入不能推出减少检查或降低诊疗成本。',
            '样本按记录划分，唯一ID不能单独证明所有采样独立性；缺少临床时间与人口学信息。',
            'SelectKBest是单变量筛选，可能保留冗余变量，不保证最优组合；五折频次仅作探索描述。',
            '测试置信区间以固定已拟合模型为条件，不包含重新划分、训练、筛选的全部不确定性。',
            '区间跨零或分数相近不证明等效；没有预设临床非劣效界值。',
            '固定阈值0.5不是临床最佳阈值；分数未作外部概率校准。',
            '没有使用真实患者资料进行诊疗决策。'],
        data_files={'group_comparisons': 'tables/group_comparisons.csv', 'cv_fold_metrics': 'tables/cv_fold_metrics.csv',
                    'test_metrics': 'tables/model_test_metrics.csv', 'selected_features': 'tables/final_selected_features.csv',
                    'selection_frequency': 'tables/feature_selection_frequency.csv',
                    'coefficients': 'tables/logistic_coefficients.csv', 'auc_comparisons': 'tables/auc_comparisons.csv'},
        provenance={'config_sha256': config_hash, 'frozen_selection_file': 'frozen_selection.json',
                    'frozen_at_utc': frozen_at, 'final_fit_started_at_utc': fit_start})
    write_json(root / 'outputs/summary.json', summary)
    print('[5/6] Summary JSON written. Creating figures.', flush=True)
    from .figures import create_figures
    figure_manifest = create_figures(root, dev, correlations, summary, cfg)

    # 最后核查计数、基线与成对比较。失败时不能宣布执行完成。
    assert split['development']['n'] + split['test']['n'] == len(raw)
    for model_id, result in model_results.items():
        metric = result['test']
        assert sum(metric[k] for k in ['tn', 'fp', 'fn', 'tp']) == len(test)
        assert metric['tp'] + metric['fn'] == split['test']['malignant']
        assert metric['tn'] + metric['fp'] == split['test']['benign']
        assert metric['auc_ci_low'] <= metric['auc_ci_high']
    assert model_results['DUMMY']['test']['auc'] == .5
    assert model_results['DUMMY']['test']['sensitivity'] == 0
    assert model_results['DUMMY']['test']['precision'] is None
    assert sha256(raw_path) == raw_hash and sha256(root / 'config.json') == config_hash
    run_manifest = dict(started_at_utc=started_at, completed_at_utc=utc_now(), elapsed_seconds=time.perf_counter()-start,
         python=platform.python_version(), platform=platform.platform(), versions=versions,
         config_sha256=config_hash, source_sha256=raw_hash, figures=figure_manifest,
         assertions_passed=['source_and_config_unchanged', 'disjoint_development_and_test',
             'same_cv_folds_for_all_models', 'per_fold_scaler_statistics_match_training_only',
             'expected_number_of_selected_features', 'test_confusion_counts_match_class_counts',
             'dummy_auc_0.5_and_zero_malignant_recall', 'no_convergence_warning', 'json_no_nan'],
         code_sha256={str(p.relative_to(root)): sha256(p) for p in [root/'run_analysis.py', *sorted((root/'src').rglob('*.py'))]},
         skill_citation='Kassis et al. (2026). Scientific Agent Skills. https://doi.org/10.48550/arXiv.2609.00065')
    write_json(root / 'outputs/run_manifest.json', run_manifest)
    print('[6/6] Finished; all assertions passed.', flush=True)
    for model_id, result in model_results.items():
        print(model_id, 'CV', result['cv']['mean_auc'], 'TEST', result['test'], flush=True)
    print('PAIRED DIFFERENCES', comparisons, flush=True)
