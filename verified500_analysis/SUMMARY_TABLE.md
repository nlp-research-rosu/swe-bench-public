# Supporting case table

These 21 detailed analyses predate the final 60-case evidence set and are kept
as supporting material. Fifteen are included in the final substantive set; six
are useful negative controls showing why a changed patch is not automatically
counted as an improvement.

## Included in the final 60

| Instance | Finding |
|---|---|
| [astropy__astropy-14096](astropy__astropy-14096/ANALYSIS.md) | Incomplete inheritance scan produces the wrong error path. |
| [django__django-11206](django__django-11206/ANALYSIS.md) | Zero-valued Decimal formatting can produce invalid-looking output. |
| [django__django-13121](django__django-13121/ANALYSIS.md) | Duration arithmetic still crashes on supported backends. |
| [django__django-13569](django__django-13569/ANALYSIS.md) | Correlated subquery grouping can be silently dropped. |
| [django__django-14170](django__django-14170/ANALYSIS.md) | Maximum ISO-year input crosses an unguarded boundary. |
| [django__django-14725](django__django-14725/ANALYSIS.md) | Edit-only formsets can still create records through an override. |
| [matplotlib__matplotlib-25960](matplotlib__matplotlib-25960/ANALYSIS.md) | Unrelated GridSpec spacing leaks into subfigure placement. |
| [psf__requests-2931](psf__requests-2931/ANALYSIS.md) | The baseline patches a caller instead of the shared encoder hazard. |
| [pydata__xarray-4094](pydata__xarray-4094/ANALYSIS.md) | Stack/unstack can silently lose length-one dimensions. |
| [scikit-learn__scikit-learn-11310](scikit-learn__scikit-learn-11310/ANALYSIS.md) | A duplicate compatibility path remains incomplete. |
| [scikit-learn__scikit-learn-13496](scikit-learn__scikit-learn-13496/ANALYSIS.md) | Constructor parameter insertion shifts positional callers. |
| [sphinx-doc__sphinx-7910](sphinx-doc__sphinx-7910/ANALYSIS.md) | Owner resolution misses narrow decorator and globals cases. |
| [sphinx-doc__sphinx-9367](sphinx-doc__sphinx-9367/ANALYSIS.md) | One-element tuple subscript syntax changes meaning. |
| [sympy__sympy-14531](sympy__sympy-14531/ANALYSIS.md) | The same printer defect remains in sibling implementations. |
| [sympy__sympy-24066](sympy__sympy-24066/ANALYSIS.md) | A clean ValueError becomes a low-level TypeError. |

## Excluded from the final 60

| Instance | Exclusion reason |
|---|---|
| [django__django-11532](django__django-11532/ANALYSIS.md) | Extra change is harmless but redundant. |
| [django__django-14434](django__django-14434/ANALYSIS.md) | Behavior is equivalent. |
| [django__django-15732](django__django-15732/ANALYSIS.md) | Behavior-preserving refactor. |
| [django__django-16454](django__django-16454/ANALYSIS.md) | Differences affect unreachable edge cases. |
| [matplotlib__matplotlib-23314](matplotlib__matplotlib-23314/ANALYSIS.md) | Defensive guard lacks a reachable trigger. |
| [sympy__sympy-12481](sympy__sympy-12481/ANALYSIS.md) | Boolean reorder and doctest are behaviorally equivalent. |

The three strongest executable demonstrations are collected in
[ENHANCED_TESTS.md](ENHANCED_TESTS.md).
