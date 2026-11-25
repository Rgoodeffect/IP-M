# منظومة التخطيط والاستثمار — شركة ليبيا للنفط (`loc_planning`)

تطبيق Frappe/ERPNext v16 يوحد أنظمة إدارة الاستثمار والتخطيط الاستراتيجي:
تقرير نشاط الشركة، الموقف التنفيذي للموازنة، المحطات والأنشطة المساندة، نشاط الإدارات،
وسجل الشركات والموردين وشهادات إثبات القيد.

## الحالة

| المرحلة | المحتوى | الحالة |
|---|---|---|
| 1 | الأساس: البيانات الرئيسية، الأدوار، الإعدادات، قفل الفترات، Workspace | منجزة |
| 2 | سجل الشركات والشهادات + الترحيل من Access | منجزة |
| 3 | المحطات والبيانات الشهرية | منجزة |
| 4 | الموازنة والموقف التنفيذي | منجزة |
| 5 | نشاط الإدارات + Workflow + التذكير | منجزة |
| 6 | تقرير النشاط المتكامل (PDF/Word) | — |
| 7 | لوحة المؤشرات + الأدلة | — |

## التثبيت

انظر [`docs/install.md`](docs/install.md)، ودليل الترحيل من Access في [`docs/migration_access.md`](docs/migration_access.md).

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
  demo_data/                  # بيانات تجريبية منفصلة (لا تحمل تلقائيا)
  utils/periods.py            # حسابات الفترات (الأسماء، التواريخ، المقارنات)
  utils/document_guard.py     # قفل الفترات المغلقة، سبب الإلغاء، منع حذف المعتمد
  utils/arabic.py             # توحيد النص العربي (كشف التكرار، إزالة التشكيل)
  utils/print_utils.py        # الخط والشعار والتواريخ في المخرجات الرسمية
  investment_registry/        # سجل الشركات، الشهادات، الترحيل، المهام اليومية
  www/verify-certificate.*    # صفحة التحقق العامة من الشهادة
  activity_report/            # نماذج نشاط الإدارات، مسار الاعتماد، المواعيد والتذكير، حالة التقارير
  budget/                     # الموازنة، التعديلات، قيود التنفيذ، الربط بدفتر الأستاذ، الموقف التنفيذي
  stations/                   # المحطات، البيانات الشهرية، الاستيراد من Excel، التقارير، التذكير
  loc_planning/               # Module: LOC Planning (Masters + Settings + Workspace + Sidebar)
  budget/ stations/ activity_report/ investment_registry/   # بقية الوحدات
  dock/ desktop_icon/         # التنقل في واجهة v16
  fixtures/role.json          # الأدوار الثمانية
  translations/ar.csv         # الترجمة العربية (مولدة)
  tests/                      # اختبارات IntegrationTestCase
dev_tools/
  gen_doctypes.py             # يولد JSON الـ DocTypes و ar.csv من المواصفات
  doctype_specs/              # مواصفات الـ DocTypes (المصدر الوحيد للحقول والتسميات)
  workflow_specs.py           # مسارات الاعتماد (تكتب إلى fixtures)
  navigation_specs.py         # القائمة الجانبية والـ Workspace
  print_format_specs.py       # قوالب الطباعة (HTML بجانب JSON)
  manual_ar.csv               # ترجمة رسائل الكود
```

### تعديل DocType

عدل المواصفة في `dev_tools/doctype_specs/` ثم:

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
