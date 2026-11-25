# معايير القبول وكيفية التحقق منها

| المعيار (الفقرة 10) | كيف يتحقق | الاختبار |
|---|---|---|
| `install-app` و`migrate` و`build` بلا أخطاء على موقع نظيف | يتم في كل مرحلة على موقع جديد (`clean.local`) | التثبيت النظيف قبل كل commit |
| حساب نسب التنفيذ والمتبقي | المعتمد والتعديلات والالتزامات والمنفذ والمتبقي والنسبة والحالة حسب العتبات | `test_budget.test_figures_and_status_thresholds`، `test_transfer_revision_and_history`، `test_gl_source_by_region_and_cancellation` |
| قيد التفرد: محطة/شهر | سجل واحد لكل محطة في الشهر | `test_stations.test_calculations_and_uniqueness` |
| قيد التفرد: إدارة/فترة | نموذج واحد لكل إدارة في الفترة | `test_activity_submissions.test_rules_uniqueness_and_template` |
| عزل الصلاحيات: إدارة لا ترى إدارة أخرى | قوائم ونماذج وتقارير ولوحة | `test_masters_and_permissions.test_department_coordinator_sees_only_own_department`، `test_activity_submissions.test_departments_see_only_their_own_reports`، `test_dashboard.test_department_coordinator_sees_only_its_department` |
| عزل الصلاحيات: مكتب مبيعات لا يرى محطات غيره | قوائم ونماذج واستيراد وتقارير ولوحة | `test_stations.test_sales_office_isolation`، `test_template_contains_only_own_stations_with_opening_stock`، `test_reports`، `test_dashboard.test_sales_office_sees_only_its_own_data` |
| منع التعديل بعد إغلاق الفترة | لكل مستند مرتبط بفترة | `test_document_guard.*`، `test_stations.test_closed_month_is_locked`، `test_budget.test_entry_in_closed_month_is_locked`، `test_activity_submissions.test_closed_period_locks_submissions` |
| ثبات لقطة التقرير بعد الاعتماد | تغير البيانات المصدرية لا يغير التقرير، ويمنع التحديث بعد الاعتماد | `test_company_activity_report.test_approval_flow_snapshot_and_inclusion` |
| PDF عربي سليم، أرقام متسقة، جداول لا تنكسر بشكل سيئ | محرك Chrome، فاصل آلاف موحد، رؤوس جداول متكررة، صفوف لا تنقسم | `test_company_activity_report.test_pdf_and_word_outputs`، `test_investment_registry.test_print_format_renders_arabic_with_qr`، مع مراجعة بصرية للصفحات |
| لا نص يوحي بأنها مولدة آليا، ولا تشكيل | المخرجات خالية من التشكيل وعبارات الآلية | `test_periods.UnitTestArabicTexts`، `test_pdf_and_word_outputs` |
| كل الإعدادات قابلة للتغيير دون كود | العتبات، الخط وملفه، الشعار، المواعيد والتذكير، صلاحية الشهادات، أنماط الترقيم، رابط التحقق | `LOC Planning Settings` و`test_budget` (`change_settings`) و`test_stations.test_reminder_schedule` |

## تشغيل الاختبارات

```bash
bench --site <site> set-config allow_tests true
bench --site <site> run-tests --app loc_planning
```
