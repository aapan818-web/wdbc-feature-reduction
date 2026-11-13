"""独立核对保存的预测、指标、数据划分和效应方向；不训练或选择模型。"""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
import pandas as pd
import joblib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.analysis import FEATURES


def close(a, b):
    assert np.isclose(a, b, rtol=1e-11, atol=1e-12), (a, b)


def main():
    summary = json.loads((ROOT / 'outputs/summary.json').read_text())
    cfg = json.loads((ROOT / 'config.json').read_text())
    raw = pd.read_csv(ROOT / 'data/raw/wdbc.csv', header=None, dtype={0: str})
    raw.columns = ['id', 'diagnosis'] + FEATURES
    assignments = pd.read_csv(ROOT / 'data/processed/split_assignments.csv', dtype={'id': str})
    folds = pd.read_csv(ROOT / 'outputs/tables/cv_fold_assignments.csv', dtype={'id': str})
    preds = pd.read_csv(ROOT / 'outputs/predictions/test_predictions.csv', dtype={'id': str})
    metrics = pd.read_csv(ROOT / 'outputs/tables/model_test_metrics.csv').set_index('model')
    boot = pd.read_csv(ROOT / 'outputs/tables/test_bootstrap_auc.csv')
    dev_idx = assignments.loc[assignments.partition == 'development', 'row_index'].to_numpy()
    test_idx = assignments.loc[assignments.partition == 'test', 'row_index'].to_numpy()
    assert len(raw) == 569 and len(FEATURES) == 30
    assert len(dev_idx) == 455 and len(test_idx) == 114
    assert set(dev_idx).isdisjoint(test_idx)
    assert set(dev_idx) | set(test_idx) == set(range(len(raw)))
    assert len(folds) == len(dev_idx) and folds.row_index.is_unique
    assert set(folds.row_index) == set(dev_idx) and set(folds.fold) == {1, 2, 3, 4, 5}
    assert set(preds.row_index) == set(test_idx) and preds.row_index.is_unique
    assert raw.iloc[preds.row_index].id.tolist() == preds.id.tolist()
    y = raw.iloc[preds.row_index].diagnosis.map({'B': 0, 'M': 1}).to_numpy()
    assert np.array_equal(y, preds.true_label.to_numpy())
    assert int(y.sum()) == 42 and int((y == 0).sum()) == 72
    assert len(boot) == 1000

    for mid, result in summary['models'].items():
        probability = preds[mid + '_probability'].to_numpy()
        predicted = (probability >= .5).astype(int)
        assert np.array_equal(predicted, preds[mid + '_prediction'].to_numpy())
        p, n = probability[y == 1], probability[y == 0]
        # 独立的成对秩定义：一个恶性分数高于一个良性分数记 1，相等记 0.5。
        auc = ((p[:, None] > n).sum() + .5 * (p[:, None] == n).sum()) / (len(p) * len(n))
        counts = dict(tn=int(((y == 0) & (predicted == 0)).sum()),
                      fp=int(((y == 0) & (predicted == 1)).sum()),
                      fn=int(((y == 1) & (predicted == 0)).sum()),
                      tp=int(((y == 1) & (predicted == 1)).sum()))
        t = result['test']
        for key, val in counts.items():
            assert val == t[key] == metrics.loc[mid, key]
        close(auc, t['auc']); close(auc, metrics.loc[mid, 'auc'])
        close(counts['tp'] / 42, t['sensitivity'])
        close(counts['tn'] / 72, t['specificity'])
        close((counts['tp'] + counts['tn']) / 114, t['accuracy'])
        low, high = np.quantile(boot[mid], [.025, .975])
        close(low, t['auc_ci_low']); close(high, t['auc_ci_high'])
        model = joblib.load(ROOT / f'outputs/models/{mid}.joblib')
        replay = model.predict_proba(raw.iloc[preds.row_index][FEATURES])[:, list(model.classes_).index(1)]
        assert np.allclose(replay, probability, rtol=1e-11, atol=1e-12)
        if mid.startswith('LR'):
            assert int(model.named_steps['scaler'].n_samples_seen_) == 455
            assert np.allclose(model.named_steps['scaler'].mean_, raw.iloc[dev_idx][FEATURES].mean())
            actual_features = np.array(FEATURES)[model.named_steps['selector'].get_support()].tolist()
            assert actual_features == result['features'] and len(actual_features) == int(mid[2:])

    for row in summary['comparisons']:
        left, right = row['contrast'].split('-')
        close(row['estimate'], summary['models'][left]['test']['auc'] - summary['models'][right]['test']['auc'])
        lo, hi = np.quantile(boot[left] - boot[right], [.025, .975])
        close(lo, row['ci_low']); close(hi, row['ci_high'])

    dev = raw.iloc[dev_idx]
    for row in summary['statistics']['features']:
        m = dev.loc[dev.diagnosis == 'M', row['feature']].to_numpy()
        b = dev.loc[dev.diagnosis == 'B', row['feature']].to_numpy()
        # 以所有两两比较独立检查 signed rank-biserial 的方向与数值。
        effect = ((m[:, None] > b).sum() - (m[:, None] < b).sum()) / (len(m) * len(b))
        close(effect, row['rank_biserial'])
    cv = pd.read_csv(ROOT / 'outputs/tables/cv_fold_metrics.csv')
    assert len(cv) == 25 and cv.groupby('model').size().eq(5).all()
    for mid, group in cv.groupby('model'):
        close(group.auc.mean(), summary['models'][mid]['cv']['mean_auc'])
        close(group.auc.std(ddof=1), summary['models'][mid]['cv']['sd_auc'])
    best_lr = sorted(cfg['default_candidates'], key=lambda m: (-summary['models'][m]['cv']['mean_auc'], int(m[2:])))[0]
    frozen = json.loads((ROOT / 'outputs/frozen_selection.json').read_text())
    assert best_lr == summary['default_model'] == frozen['default_model']
    assert frozen['frozen_at_utc'] <= summary['provenance']['final_fit_started_at_utc']
    sha = hashlib.sha256((ROOT / 'data/raw/wdbc.csv').read_bytes()).hexdigest()
    assert sha == summary['source']['sha256']
    evidence = {
        'status': 'passed', 'scope': 'saved data, fold membership, saved estimators, predictions and numerical summaries',
        'checks': ['569 original rows; disjoint 455/114 partitions', 'CV validation memberships cover development rows once',
                   'test labels match original data', 'manual pairwise AUC and confusion counts match all 5 models',
                   'saved estimator predictions reproduce CSV', 'final LR scalers use development data only',
                   'selected feature names and counts match fitted models', 'paired-bootstrap intervals reproduce from saved draws',
                   'rank-biserial signs and values match pairwise comparisons', 'default LR chosen by CV before test',
                   'source hash matches manifest'],
        'limits': 'Does not establish external validity, sampling independence, clinical utility or user understanding.'
    }
    (ROOT / 'outputs/independent_verification.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
