import frappe


def execute():
	"""Add a database index on Fees.student_id and Fees.family_code.

	Both fields are Custom Fields (not part of fees.json), so their index
	setting lives only in each site's database and doesn't travel with the
	app's code - hence this patch, so every site picks it up on migrate.
	"""
	for fieldname in ("student_id", "family_code"):
		name = frappe.db.get_value("Custom Field", {"dt": "Fees", "fieldname": fieldname})
		if not name:
			continue

		doc = frappe.get_doc("Custom Field", name)
		if doc.search_index:
			continue

		doc.search_index = 1
		doc.save()
