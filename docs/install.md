# دليل التثبيت

## المتطلبات (ERPNext v16)

| المكون | الإصدار |
|---|---|
| Frappe / ERPNext | 16.x (جرب على 16.61.0) |
| Python | 3.14 |
| Node.js | 24 |
| MariaDB | 10.6 – 11.8 (utf8mb4) |
| Redis | 6+ |

## موقع جديد

```bash
cd ~/frappe-bench
bench get-app https://github.com/Rgoodeffect/ip-m --branch <branch>
bench new-site <site> --install-app erpnext
bench --site <site> install-app loc_planning
bench --site <site> migrate
bench build --app loc_planning
```

ثم أكمل معالج إعداد ERPNext:
- **اللغة**: العربية. المعالج يعيد ضبط لغة النظام، فاخترها فيه.
- **الدولة**: Libya، **العملة**: LYD، **السنة المالية**: من 1 يناير إلى 31 ديسمبر.
- **الشركة**: Oilibya.

## ما يحدث عند التثبيت

| ما ينشأ | المصدر | ملاحظات |
|---|---|---|
| الأدوار التسعة (الثمانية + المدير العام) | `fixtures/role.json` | تنشأ أيضا في `after_install` / `after_migrate` |
| المنطقتان (الغربية W، الشرقية E) | `setup_data/regions.json` | |
| الهيكل التنظيمي (24 جهة) | `setup_data/departments.json` | للمنطقة الغربية |
| المنتجات الأربعة | `setup_data/fuel_products.json` | الوقود باللتر، الغاز بالأسطوانة (وحدة `Cylinder`) |
| القيم الافتراضية للإعدادات | `LOC Planning Settings` | عتبات 40% / 80%، خط Fanan، عملة LYD |
| لغة النظام | العربية | فقط إذا كانت الإنجليزية |

التحميل لا يكرر أي سجل موجود ولا يعدله. لإعادة تشغيله يدويا:

```bash
bench --site <site> execute loc_planning.install.seed_master_data
```

## بعد التثبيت

1. **الإعدادات**: افتح "إعدادات منظومة التخطيط والاستثمار" واختر الشركة، وارفع الشعار وملف خط Fanan.
2. **الفترات**: من نفس الصفحة، اختر السنة واضغط "إنشاء فترات السنة". تنشأ 12 شهرا و4 أرباع ونصفان وسنة.
3. **المستخدمون**: من "ربط المستخدمين بالأدوار والجهات" أضف صفا لكل مستخدم ودوره وجهته، ثم اضغط "تطبيق".
   - دور "منسق إدارة" يتطلب تحديد الإدارة.
   - دور "مكتب مبيعات" يتطلب تحديد مكتب مبيعات.

## صفحة التحقق من الشهادات

رمز QR في الشهادة يشير إلى `/verify-certificate?code=...`. الصفحة عامة (بدون تسجيل دخول) وتعرض فقط: رقم الشهادة، اسم الشركة، التصنيف، تاريخي الإصدار والانتهاء، والحالة.

إن كان الموقع يعمل خلف عنوان داخلي، اضبط "رابط موقع التحقق" في الإعدادات على العنوان العام قبل إصدار الشهادات.

## ملفات PDF

قوالب الطباعة تستخدم محرك Chrome في v16 لأنه يعرض العربية بشكل صحيح.

- على الخادم: نفذ `bench setup-chrome`.
- أو استخدم Chromium موجودا مسبقا: `bench config set-common-config -c chromium_path '"/path/to/chrome"'`.

## التحقق

```bash
bench --site <site> set-config allow_tests true
bench --site <site> run-tests --app loc_planning
```
