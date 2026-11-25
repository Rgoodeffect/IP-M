# منظومة التخطيط والاستثمار — شركة ليبيا للنفط (`loc_planning`)

تطبيق Frappe/ERPNext v16 يوحّد أنظمة إدارة الاستثمار والتخطيط الاستراتيجي:
تقرير نشاط الشركة، الموقف التنفيذي للموازنة، المحطات والأنشطة المساندة، نشاط الإدارات،
وسجل الشركات والموردين وشهادات إثبات القيد.

## الحالة

| المرحلة | المحتوى | الحالة |
|---|---|---|
| 1 | الأساس: البيانات الرئيسية، الأدوار، الإعدادات، قفل الفترات، Workspace | منجزة |
| 2 | سجل الشركات والشهادات + الترحيل من Access | — |
| 3 | المحطات والبيانات الشهرية | — |
| 4 | الموازنة والموقف التنفيذي | — |
| 5 | نشاط الإدارات + Workflow + التذكير | — |
| 6 | تقرير النشاط المتكامل (PDF/Word) | — |
| 7 | لوحة المؤشرات + الأدلة | — |

## التثبيت

انظر [`docs/install.md`](docs/install.md).

```bash
bench get-app https://github.com/Rgoodeffect/ip-m --branch <branch>
bench --site <site> install-app loc_planning
bench --site <site> migrate
bench build --app loc_planning
```

## هيكل المستودع

```
loc_planning/                 # الحزمة (app)
  hooks.py                    # fixtures, doc_events, after_install/after_migrate
  install.py                  # تحميل البيانات الأولية (idempotent)
  constants.py                # أسماء الأدوار والوحدات والحقول المشتركة
  setup_data/*.json           # البيانات الأولية الرسمية (مناطق، منتجات، هيكل تنظيمي)
  demo_data/                  # بيانات تجريبية منفصلة (لا تُحمّل تلقائياً)
  utils/periods.py            # حسابات الفترات (الأسماء، التواريخ، المقارنات)
  utils/document_guard.py     # قفل الفترات المغلقة، سبب الإلغاء، منع حذف المعتمد
  loc_planning/               # Module: LOC Planning (Masters + Settings + Workspace + Sidebar)
  budget/ stations/ activity_report/ investment_registry/   # بقية الوحدات
  dock/ desktop_icon/         # التنقل في واجهة v16
  fixtures/role.json          # الأدوار الثمانية
  translations/ar.csv         # الترجمة العربية (مولّدة)
  tests/                      # اختبارات IntegrationTestCase
dev_tools/
  gen_doctypes.py             # يولّد JSON الـ DocTypes و ar.csv من المواصفات
  doctype_specs/              # مواصفات الـ DocTypes (المصدر الوحيد للحقول والتسميات)
  manual_ar.csv               # ترجمة رسائل الكود
```

### تعديل DocType

عدّل المواصفة في `dev_tools/doctype_specs/` ثم:

```bash
python3 dev_tools/gen_doctypes.py
bench --site <site> migrate
```

## الاختبارات

```bash
bench --site <site> set-config allow_tests true
bench --site <site> run-tests --app loc_planning
```

## الترخيص

MIT
