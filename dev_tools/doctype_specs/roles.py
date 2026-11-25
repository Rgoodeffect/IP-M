"""Role names and DocPerm helpers shared by all DocType specs."""

SM = "System Manager"
DIR = "LOC Planning Director"
SP = "Strategic Planning"
SD = "Statistics & Data"
INV = "Investment Section"
DC = "Department Coordinator"
SO = "Sales Office User"
FB = "Finance Budget"
EV = "Executive Viewer"
GM = "LOC General Manager"

ALL_LOC_ROLES = [DIR, SP, SD, INV, DC, SO, FB, EV, GM]

ROLE_LABELS_AR = {
	DIR: "مدير إدارة الاستثمار والتخطيط الاستراتيجي",
	SP: "قسم التخطيط الاستراتيجي",
	SD: "قسم الإحصاء والبيانات",
	INV: "قسم الاستثمار",
	DC: "منسق إدارة",
	SO: "مكتب مبيعات",
	FB: "الإدارة المالية - الموازنة",
	EV: "الإدارة العليا",
	GM: "المدير العام",
}


def perm(
	role,
	full=False,
	write=False,
	create=None,
	delete=False,
	submit=False,
	cancel=False,
	amend=False,
	permlevel=0,
	single=False,
	if_owner=False,
):
	"""Build a DocPerm dict. `full` = every right including delete."""
	if full:
		write = create = delete = True
	if create is None:
		create = write
	p = {
		"role": role,
		"permlevel": permlevel,
		"read": 1,
		"write": int(bool(write)),
		"create": int(bool(create)),
		"delete": int(bool(delete)),
		"submit": int(bool(submit)),
		"cancel": int(bool(cancel)),
		"amend": int(bool(amend)),
		"print": 1,
		"email": 1,
		"share": int(bool(write)),
	}
	if not single:
		p.update({"report": 1, "export": 1})
	if if_owner:
		p["if_owner"] = 1
	if permlevel:
		for k in ("create", "delete", "submit", "cancel", "amend", "print", "email", "share", "export"):
			p.pop(k, None)
	return p


def read_perms(roles, single=False):
	return [perm(r, single=single) for r in roles]
