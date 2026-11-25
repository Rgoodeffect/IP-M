"""Print formats. The Jinja/HTML lives next to the generated JSON in `<name>.html`;
`gen_doctypes.py` embeds it into `<name>.json` so the format is synced on migrate."""

PRINT_FORMATS = [
	{
		"name": "Registration Certificate",
		"doc_type": "Registration Certificate",
		"module": "Investment Registry",
		"margins": (12, 12, 12, 12),
		"page_number": "Hide",
	},
]
