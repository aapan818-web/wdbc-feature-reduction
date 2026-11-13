"""从真实分析产物生成图形；英文坐标避免系统中文字体差异。

全部图导出 PNG（300 dpi）和 PDF（矢量文字），白色背景、固定尺寸。
每张图的来源、处理、样本单位、误差条含义记录在 figure_manifest.json。
"""
from pathlib import Path
import hashlib
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
import numpy as np
from PIL import Image
from scipy import stats

STYLE = {'font.family': 'DejaVu Sans', 'font.size': 10,
         'axes.titlesize': 12, 'axes.labelsize': 10, 'xtick.labelsize': 9,
         'ytick.labelsize': 9, 'legend.fontsize': 9, 'axes.spines.top': False,
         'axes.spines.right': False, 'axes.edgecolor': '#36434B',
         'axes.labelcolor': '#24333D', 'text.color': '#24333D',
         'xtick.color': '#24333D', 'ytick.color': '#24333D',
         'figure.facecolor': 'white', 'axes.facecolor': 'white',
         'savefig.facecolor': 'white', 'pdf.fonttype': 42, 'ps.fonttype': 42,
         'axes.grid': False}
COLORS = {'DUMMY': '#666666', 'LR30': '#00689D', 'LR10': '#B35400',
          'LR5': '#007A58', 'RF30': '#8D438D'}


def create_figures(root, dev, correlations, summary, cfg):
    """所有绘图输入均来自同一划分和同一批真实运行结果。"""
    root = Path(root)
    out = root / 'outputs/figures'
    manifest = []

    def export(fig, stem, title, description, source, uncertainty='None', transformations=None):
        paths = []
        for extension in ['png', 'pdf']:
            path = out / (stem + '.' + extension)
            fig.savefig(path, dpi=300, facecolor='white', transparent=False)
            paths.append(str(path.relative_to(root / 'outputs')))
        plt.close(fig)
        with Image.open(out / (stem + '.png')) as image:
            rgba = image.convert('RGBA')
            opaque = rgba.getchannel('A').getextrema() == (255, 255)
            metadata = dict(pixels=list(image.size), dpi=list(image.info.get('dpi', [])),
                            mode=image.mode, opaque=opaque)
        manifest.append(dict(stem=stem, title=title, alt_text=description, source_data=source,
             uncertainty=uncertainty, transformations=transformations or [],
             paths=paths, raster_metadata=metadata,
             sha256={path: hashlib.sha256((root/'outputs'/path).read_bytes()).hexdigest() for path in paths},
             destination='General course report and website; no journal-specific compliance claim.'))

    with plt.rc_context(STYLE):
        # 预设三项变量：原始值全部显示，不删离群点。
        fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.7), layout='constrained')
        rng = np.random.default_rng(cfg['plot_seed'])
        group_labels = ['Benign (B)', 'Malignant (M)']
        for ax, feature in zip(axes, cfg['descriptive_features']):
            values = [dev.loc[dev.target == cls, feature].to_numpy() for cls in [0, 1]]
            box = ax.boxplot(values, positions=[0, 1], widths=.48, patch_artist=True,
                             showfliers=False, medianprops={'color': '#111111', 'linewidth': 1.6},
                             boxprops={'edgecolor': '#36434B'}, whiskerprops={'color': '#36434B'},
                             capprops={'color': '#36434B'})
            for patch in box['boxes']:
                patch.set(facecolor='#F0F3F5')
            for cls, (a, color, marker) in enumerate(zip(values, ['#00689D', '#B35400'], ['o', '^'])):
                x = cls + rng.uniform(-.13, .13, len(a))
                ax.scatter(x, a, s=9, color=color, marker=marker, alpha=.38, linewidths=0, zorder=2)
            ax.set_xticks([0, 1], [f'B (n={len(values[0])})', f'M (n={len(values[1])})'])
            ax.set(title=feature, ylabel='Recorded feature value')
        fig.suptitle(f'Development-set feature distributions (n={len(dev)})', fontsize=13)
        export(fig, 'feature_distributions', 'Prespecified feature distributions',
               'Box plots and all observed development values for mean radius, texture and smoothness, separated by benign and malignant labels.',
               'data/processed/wdbc_labeled.csv + data/processed/split_assignments.csv',
               'Box: median and IQR; whiskers: 1.5 IQR; all points retained, including extreme values.',
               ['Development records only', 'Horizontal jitter for readability; seed fixed; vertical values unmodified'])

        fig, ax = plt.subplots(figsize=(9.7, 9.0), layout='constrained')
        matrix = correlations.to_numpy()
        image = ax.imshow(matrix, cmap='RdBu_r', norm=TwoSlopeNorm(vmin=-1, vcenter=0, vmax=1), interpolation='nearest')
        ax.set_xticks(np.arange(len(correlations)), correlations.columns, rotation=90, fontsize=7)
        ax.set_yticks(np.arange(len(correlations)), correlations.index, fontsize=7)
        ax.set_title(f'Spearman correlations: development data (n={len(dev)})', pad=12)
        for pos in [9.5, 19.5]:
            ax.axhline(pos, color='white', linewidth=1.2)
            ax.axvline(pos, color='white', linewidth=1.2)
        fig.colorbar(image, ax=ax, shrink=.72, label='Spearman rank correlation')
        export(fig, 'spearman_heatmap', 'Development-set feature correlations',
               'A 30 by 30 Spearman correlation heatmap, fixed from -1 to +1; white separators mark mean, standard-error and worst feature families. Numerical matrix is available as a CSV.',
               'tables/spearman_correlations.csv', transformations=['Development records only; Spearman rank correlation'])

        model_ids = ['DUMMY', 'LR30', 'LR10', 'LR5', 'RF30']
        fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.2), sharey=True, layout='constrained')
        for idx, model_id in enumerate(model_ids):
            model = summary['models'][model_id]
            mean, sd = model['cv']['mean_auc'], model['cv']['sd_auc']
            fold_scores = model['cv']['fold_auc']
            axes[0].scatter(idx + np.linspace(-.08, .08, len(fold_scores)), fold_scores,
                            marker='.', color='#687D89', s=26, alpha=.7)
            axes[0].errorbar(idx, mean, yerr=sd, color=COLORS[model_id], marker='o',
                             capsize=4, linewidth=1.4, markersize=6)
            test = model['test']
            axes[1].errorbar(idx, test['auc'], yerr=np.array([[test['auc']-test['auc_ci_low']],
                             [test['auc_ci_high']-test['auc']]]), color=COLORS[model_id],
                             marker='s', capsize=4, linewidth=1.4, markersize=6)
        for ax in axes:
            ax.set_xticks(range(len(model_ids)), model_ids, rotation=20)
            ax.set(ylim=(.45, 1.035), ylabel='ROC-AUC')
            ax.axhline(.5, color='#808080', linestyle='--', linewidth=.8)
            ax.grid(axis='y', alpha=.18)
        axes[0].set_title('Development CV: mean ± SD (5 folds)')
        axes[1].set_title(f'Test: conditional 95% bootstrap CI (n={summary["split"]["test"]["n"]})')
        export(fig, 'model_performance', 'Prespecified model comparison',
               'Five models compared on a common ROC-AUC scale. Left: individual validation-fold scores, mean and SD. Right: test AUC with fixed-model conditional percentile confidence intervals. SD is not a confidence interval.',
               'tables/model_cv_summary.csv + tables/cv_fold_metrics.csv + tables/model_test_metrics.csv',
               'Left: sample SD across 5 correlated folds; right: 95% stratified percentile bootstrap, 1000 paired resamples; fixed models.')

        fig, ax = plt.subplots(figsize=(6.6, 5.5), layout='constrained')
        styles = {'DUMMY': ':', 'LR30': '-', 'LR10': '--', 'LR5': '-.', 'RF30': (0, (3, 1, 1, 1))}
        for model_id in model_ids:
            model = summary['models'][model_id]
            ax.plot(model['roc']['fpr'], model['roc']['tpr'], color=COLORS[model_id],
                     linestyle=styles[model_id], linewidth=1.7,
                     label=f'{model_id}: AUC {model["test"]["auc"]:.3f}')
        ax.set(xlim=(-.015, 1.015), ylim=(-.015, 1.015), xlabel='False positive rate (1 - specificity)',
               ylabel='True positive rate (malignant sensitivity)', title='ROC curves on the same held-out test records')
        ax.legend(loc='lower right', frameon=True)
        ax.set_aspect('equal', adjustable='box')
        export(fig, 'test_roc', 'Held-out ROC curves',
               'ROC curves for the five prespecified models, using malignant probabilities on identical test records. Color and line styles distinguish models.',
               'predictions/test_predictions.csv', transformations=['Positive label M=1; ROC from continuous probabilities, not predicted classes'])

        for model_id in model_ids:
            metric = summary['models'][model_id]['test']
            cm = np.array([[metric['tn'], metric['fp']], [metric['fn'], metric['tp']]])
            fig, ax = plt.subplots(figsize=(4.6, 4.3), layout='constrained')
            image = ax.imshow(cm, cmap='Blues', vmin=0, vmax=max(summary['split']['test']['benign'], summary['split']['test']['malignant']))
            for row in range(2):
                for col in range(2):
                    ax.text(col, row, str(cm[row, col]), ha='center', va='center', fontsize=20,
                             color='white' if cm[row,col] > summary['split']['test']['benign']*.55 else '#122B39')
            ax.set_xticks([0, 1], ['Benign (0)', 'Malignant (1)'])
            ax.set_yticks([0, 1], ['Benign (0)', 'Malignant (1)'])
            ax.set(xlabel='Predicted label', ylabel='True label', title=f'{model_id} | threshold = 0.50')
            fig.colorbar(image, ax=ax, shrink=.75, label='Test records')
            export(fig, 'confusion_'+model_id, model_id+' test confusion matrix',
                   f'Rows are true classes and columns are predicted classes. TN={metric["tn"]}, FP={metric["fp"]}, FN={metric["fn"]}, TP={metric["tp"]}. Fixed threshold 0.5. Same count scale for every model.',
                   'tables/model_test_metrics.csv', transformations=['Probabilities >= 0.5 assigned malignant'])

        frequencies = {model: {r['feature']:r['count'] for r in summary['models'][model]['feature_selection_frequency']}
                       for model in ['LR5','LR10']}
        selected_union = sorted([feature for feature in correlations.index if any(frequencies[m][feature] for m in frequencies)],
                                key=lambda f: (-frequencies['LR5'][f], -frequencies['LR10'][f], f))
        values = np.array([[frequencies[m][feature] for m in ['LR5','LR10']] for feature in selected_union])
        fig, ax = plt.subplots(figsize=(6.0, max(4.4,len(selected_union)*.28+1.3)), layout='constrained')
        image = ax.imshow(values, cmap='Blues', vmin=0, vmax=5, aspect='auto')
        for row in range(values.shape[0]):
            for col in range(2):
                ax.text(col,row,str(values[row,col]),ha='center',va='center',color='white' if values[row,col]>=3 else '#122B39')
        ax.set_xticks([0,1], ['LR5', 'LR10'])
        ax.set_yticks(np.arange(len(selected_union)), selected_union, fontsize=9)
        ax.set_title('Feature selections across 5 CV training folds')
        fig.colorbar(image, ax=ax, ticks=range(6), shrink=.75, label='Selection count (0–5)')
        export(fig,'selection_frequency','Exploratory selection stability',
               'Count of CV training folds selecting each feature for LR5 and LR10. Only features selected at least once are plotted; complete counts for all 30 variables are in the CSV. Counts are descriptive, not inclusion probabilities.',
               'tables/feature_selection_frequency.csv', transformations=['Count only; features never selected omitted from this plot but retained in CSV'])

        fig, axes = plt.subplots(1,3,figsize=(13.0,8.0),layout='constrained')
        for ax, model_id in zip(axes,['LR5','LR10','LR30']):
            coefficients = sorted(summary['models'][model_id]['coefficients'], key=lambda r:r['coefficient'])
            y = np.arange(len(coefficients))
            ax.barh(y,[r['coefficient'] for r in coefficients],color=COLORS[model_id],edgecolor='#354650',linewidth=.3)
            ax.set_yticks(y,[r['feature'] for r in coefficients],fontsize=8)
            ax.axvline(0,color='#111111',linewidth=.8)
            ax.set(title=model_id,xlabel='Coefficient per training SD\n(log-odds scale)',xlim=(-2.4,2.4))
            # 避免固定范围剪裁；若系数超出，三个面板将统一扩展。
        bound=max(abs(r['coefficient']) for m in ['LR5','LR10','LR30'] for r in summary['models'][m]['coefficients'])
        for ax in axes:ax.set_xlim(-max(2.4,bound*1.15),max(2.4,bound*1.15))
        fig.suptitle('Final development-fitted logistic coefficients; not causal effects',fontsize=13)
        export(fig,'logistic_coefficients','Standardized model coefficients',
               'Signed coefficients for the three final logistic models, each using its full-development-set scaler and selected features. Axes share a coefficient range. Coefficients describe model-conditional associations, not causal effects or uncertainty intervals.',
               'tables/logistic_coefficients.csv', transformations=['Input standardized using full development mean and SD; L2-regularized coefficients'])

        fig,ax=plt.subplots(figsize=(7.4,3.1),layout='constrained')
        for y,row in enumerate(summary['comparisons']):
            ax.errorbar(row['estimate'],y,xerr=np.array([[row['estimate']-row['ci_low']],[row['ci_high']-row['estimate']]]),
                        marker='o',color=COLORS[row['contrast'].split('-')[0]],capsize=5,linewidth=1.5)
            ax.text(.98,y+.16,f'{row["estimate"]:+.4f} [{row["ci_low"]:+.4f}, {row["ci_high"]:+.4f}]',
                    transform=ax.get_yaxis_transform(),ha='right',va='bottom',fontsize=9)
        ax.set_yticks(range(2),[r['contrast'] for r in summary['comparisons']])
        ax.axvline(0,color='#444444',linestyle='--',linewidth=1)
        lo=min([0]+[r['ci_low'] for r in summary['comparisons']]);hi=max([0]+[r['ci_high'] for r in summary['comparisons']]);pad=max((hi-lo)*.15,.003)
        ax.set(xlim=(lo-pad,hi+pad),ylim=(-.5,1.6),xlabel='Test ROC-AUC difference (reduced - LR30)',
               title='Paired stratified bootstrap: conditional 95% intervals')
        export(fig,'auc_differences','Paired test AUC differences',
               'Differences in test ROC-AUC for LR5 minus LR30 and LR10 minus LR30 with paired stratified percentile 95% bootstrap intervals. A zero-crossing interval does not establish equivalence.',
               'tables/auc_comparisons.csv',uncertainty='95% percentile intervals from 1000 paired resamples, stratified by true class; models fixed.')

        # 诊断图补充数值屏查；不根据图或检验结果删除极端值或切换检验。
        fig,axes=plt.subplots(3,2,figsize=(8.5,10.3),layout='constrained')
        for row,feature in enumerate(cfg['descriptive_features']):
            for col,cls in enumerate([0,1]):
                values=dev.loc[dev.target==cls,feature].to_numpy()
                (theoretical,ordered),(slope,intercept,_) = stats.probplot(values,dist='norm')
                ax=axes[row,col]
                ax.scatter(theoretical,ordered,s=10,color=['#00689D','#B35400'][col],marker=['o','^'][col],alpha=.6)
                ax.plot(theoretical,slope*theoretical+intercept,color='#444444',linestyle='--',linewidth=1)
                ax.set(title=f'{feature} | {"B" if cls==0 else "M"} (n={len(values)})',xlabel='Normal theoretical quantile',ylabel='Observed value')
        export(fig,'diagnostic_qq','Development distribution diagnostics',
               'Six groupwise Q-Q plots for the three prespecified features. Deviations describe distribution shapes; they neither certify independence nor automatically select the hypothesis test.',
               'diagnostics.json + data/processed/wdbc_labeled.csv',transformations=['Development records only; no outlier deletion or test switching'])
    (root/'outputs/figure_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    return manifest
