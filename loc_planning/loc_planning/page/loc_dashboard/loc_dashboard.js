// لوحة المؤشرات — data from loc_planning.dashboard.api.get_dashboard_data (permission aware)

frappe.pages["loc-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("LOC Dashboard"), single_column: true });
	const dash = new LOCDashboard(page);
	wrapper.loc_dashboard = dash;
};

frappe.pages["loc-dashboard"].on_page_show = function (wrapper) {
	wrapper.loc_dashboard && wrapper.loc_dashboard.refresh();
};

class LOCDashboard {
	constructor(page) {
		this.page = page;
		this.period = page.add_field({
			fieldname: "reporting_period",
			label: __("Period"),
			fieldtype: "Link",
			options: "Reporting Period",
			change: () => this.refresh(),
		});
		this.region = page.add_field({
			fieldname: "region",
			label: __("Region"),
			fieldtype: "Link",
			options: "LOC Region",
			change: () => this.refresh(),
		});
		page.set_secondary_action(__("Refresh"), () => this.refresh());
		this.$body = $(`<div class="loc-dashboard"></div>`).appendTo(page.main);
	}

	refresh() {
		frappe
			.call({
				method: "loc_planning.dashboard.api.get_dashboard_data",
				args: { period: this.period.get_value() || null, region: this.region.get_value() || null },
			})
			.then((r) => this.render(r.message || {}));
	}

	render(d) {
		if (!this.period.get_value() && d.period) this.period.set_value(d.period);
		const fmt = (v) => format_number(v || 0, null, 0);
		const cards = [];
		if (d.sales)
			cards.push([__("Fuel Sales (Litre)"), fmt(d.sales.fuel_litres), d.sales.fuel_achievement != null ? __("Achievement") + ` ${flt(d.sales.fuel_achievement, 1)}%` : "", "blue"]);
		if (d.budget)
			cards.push([__("Budget Execution"), `${flt(d.budget.execution_pct, 1)}%`, d.budget.status_label, "green"]);
		if (d.stations) cards.push([__("Operating Stations"), `${d.stations.operating} / ${d.stations.total}`, "", "orange"]);
		if (d.reports)
			cards.push([__("Department Reports Received"), `${d.reports.received} / ${d.reports.required}`, d.reports.period_title, "purple"]);
		if (d.certificates) cards.push([__("Certificates Issued"), fmt(d.certificates.issued), d.period_title, "cyan"]);

		this.$body.html(`
			<div class="loc-cards">${cards
				.map(
					([label, value, sub, color]) => `
				<div class="loc-card">
					<div class="loc-card-label">${frappe.utils.escape_html(label)}</div>
					<div class="loc-card-value" style="color: var(--${color}-600)">${frappe.utils.escape_html(value)}</div>
					<div class="loc-card-sub">${frappe.utils.escape_html(sub || "")}</div>
				</div>`
				)
				.join("")}</div>
			<div class="loc-charts">
				<div class="loc-chart-box"><div class="loc-chart-title">${__("Target vs actual fuel sales by month (Litre)")}</div><div class="chart-trend"></div></div>
				<div class="loc-chart-box"><div class="loc-chart-title">${__("Fuel sales by product")}</div><div class="chart-products"></div></div>
				<div class="loc-chart-box"><div class="loc-chart-title">${__("Budget execution by chapter")}</div><div class="chart-budget"></div></div>
			</div>
			<div class="loc-table-box"><div class="loc-chart-title">${__("Department Activity Status")}${d.reports ? " - " + frappe.utils.escape_html(d.reports.period_title || "") : ""}</div><div class="table-reports"></div></div>
		`);

		const chart = (selector, data, type, extra) => {
			const el = this.$body.find(selector)[0];
			if (!data || !data.labels || !data.labels.length) {
				$(el).html(`<div class="text-muted small p-3">${__("No data")}</div>`);
				return;
			}
			new frappe.Chart(el, Object.assign({ data, type, height: 240, colors: ["#1f4e79", "#6fa8dc", "#c9a227", "#7f7f7f"] }, extra || {}));
		};
		if (d.trend)
			chart(".chart-trend", {
				labels: d.trend.map((m) => m.label),
				datasets: [
					{ name: __("Target"), values: d.trend.map((m) => Math.round(m.target)) },
					{ name: __("Actual Sales"), values: d.trend.map((m) => Math.round(m.actual)) },
				],
			}, "line");
		if (d.sales) {
			const fuel = d.sales.products.filter((p) => p.uom === "Litre");
			chart(".chart-products", { labels: fuel.map((p) => p.product), datasets: [{ values: fuel.map((p) => Math.round(p.actual)) }] }, "pie");
		}
		if (d.budget)
			chart(".chart-budget", {
				labels: d.budget.chapters.map((c) => c.chapter),
				datasets: [
					{ name: __("Approved Amount"), values: d.budget.chapters.map((c) => Math.round(c.approved)) },
					{ name: __("Executed"), values: d.budget.chapters.map((c) => Math.round(c.executed)) },
				],
			}, "bar");
		["trend", "products", "budget"].forEach((k) => {
			const has = { trend: d.trend, products: d.sales, budget: d.budget }[k];
			if (!has) this.$body.find(`.chart-${k}`).closest(".loc-chart-box").remove();
		});

		const colors = { "Not Submitted": "red", Draft: "gray", Returned: "red", "Manager Review": "blue", "Statistics Review": "orange", "Planning Approval": "orange", Approved: "green", "Included in Report": "green" };
		const $t = this.$body.find(".table-reports");
		if (!d.reports) {
			$t.closest(".loc-table-box").remove();
			return;
		}
		$t.html(`<table class="table table-bordered loc-status-table">
			<thead><tr><th>${__("Department")}</th><th>${__("Status")}</th><th>${__("Due Date")}</th><th>${__("Days Late")}</th><th>${__("Overall Achievement")}</th></tr></thead>
			<tbody>${d.reports.rows
				.map(
					(r) => `<tr>
					<td>${r.submission ? `<a href="/app/department-activity-submission/${encodeURIComponent(r.submission)}">${frappe.utils.escape_html(r.department)}</a>` : frappe.utils.escape_html(r.department)}</td>
					<td><span class="indicator-pill ${colors[r.state] || "gray"}">${frappe.utils.escape_html(r.state_label)}</span></td>
					<td>${r.due_date ? frappe.datetime.str_to_user(r.due_date) : ""}</td>
					<td>${r.days_late ? `<span style="color: var(--red-600)">${r.days_late}</span>` : "0"}</td>
					<td>${r.achievement != null ? flt(r.achievement, 1) + "%" : ""}</td>
				</tr>`
				)
				.join("")}</tbody></table>`);
	}
}
