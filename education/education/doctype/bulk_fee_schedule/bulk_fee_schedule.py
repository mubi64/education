# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BulkFeeSchedule(Document):
	def on_submit(self):
		for fee in self.schedule_month:
			fee_doc = frappe.get_doc({
				"doctype": "Fees",
				"student": self.student,
				"set_posting_time": 1,
				"posting_date": fee.posting_date,
				"due_date": fee.due_date,
				"fee_structure": self.fee_structure,
				"program": self.program,
			})
			for com in self.components:
				fee_doc.append("components", {
					"fees_category": com.fees_category,
					"gross_amount": com.gross_amount,
					"description": com.description,
					"amount": com.amount
				})
			fee_doc.save()
