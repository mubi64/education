# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import erpnext
import frappe
from frappe import _

from frappe.model.document import Document
from frappe.utils.background_jobs import enqueue
from frappe.utils import cstr, add_months, add_days, flt
from education.education.api import get_current_enrollment


class TransportationFeeSchedule(Document):
	def onload(self):
		info = self.get_dashboard_info()
		self.set_onload("dashboard_info", info)

	def get_dashboard_info(self):
		info = {
			"total_paid": 0,
			"total_unpaid": 0,
			"currency": erpnext.get_company_currency(self.company),
		}

		# fees_amount = frappe.db.sql(
		# 	"""select sum(grand_total), sum(outstanding_amount) from tabFees
		# 	where fee_schedule=%s and docstatus=1""",
		# 	(self.name),
		# )

		# if fees_amount:
		# 	info["total_paid"] = flt(fees_amount[0][0]) - \
		# 		flt(fees_amount[0][1])
		# 	info["total_unpaid"] = flt(fees_amount[0][1])

		return info

	def validate(self):
		if self.total_student == 0:
			frappe.throw(_("Please get student first"))
	@frappe.whitelist()
	def create_fees(self):
		if self.total_student > 10:
			frappe.msgprint(
				_(
					"""Fee records will be created in the background.
				In case of any error the error message will be updated in the Schedule."""
				)
			)
			enqueue(
				self.generate_fee,
				queue="default",
				timeout=6000,
				event="generate_fee",
			)
		else:
			self.generate_fee()
	
	def generate_fee(self):
		students = frappe.db.get_all("Student", filters=[
			["transportation_fee_structure", "is", "set"],
			["enabled", "=", 1]
		], fields=['name'])
		if len(students) > 0:
			created_records = 0
			error = False
			for st in students:
				enrollment = get_current_enrollment(st.name)
				# print(student, self.posting_date, self.due_date, "cchek student")
				one_month_earlier = add_months(self.posting_date, -1)
				result_date = add_days(one_month_earlier, 1)
				# print(enrollment, "testing **************************")
				# frappe.throw(str(enrollment))
				student = frappe.get_doc("Student", st.name, fields=['*'])
				trans_student = frappe.get_doc("Transportation Fee Structure", student.transportation_fee_structure, fields=['*'])
				fee = frappe.db.get_all("Fees", filters=[
						['docstatus', "!=", 2],
						['posting_date', 'between', [result_date, self.posting_date]],
						['student', "=", student.name],
						['Fee Component', 'fees_category', '=', trans_student.fee_category]
					], fields=["*"])
				if len(fee) == 0:
					try:
						# fees_category_array = []
						stu_months_array = []
						tran_months_array = []

						# for comp in self.components:
						# 	fees_category_array.append(comp.fees_category)

						for m in student.transportation_fee_structure_months:
							stu_months_array.append(m.month_number)

						for m in trans_student.transportation_fee_structure_months:
							tran_months_array.append(m.month_number)
						posting_month = frappe.utils.formatdate(self.posting_date, "MM")
						if frappe.utils.getdate(str(self.posting_date)) >= frappe.utils.getdate(str(student.start_date)):
							if posting_month in stu_months_array or posting_month not in tran_months_array:
								pass
								# for comp in self.components:
								# 	if comp.fees_category == trans_student.fee_category:
								# 		self.components.remove(comp)
							# el
							elif (posting_month in tran_months_array): # and trans_student.dependant_fee_category in fees_category_array
								fee = frappe.new_doc('Fees')
								fee.student = student.name
								fee.program = enrollment.program
								fee.posting_date = self.posting_date
								fee.transportation_fee_schedule = self.name
								fee.due_date = self.due_date
								fee.components = []
								fee.append('components', {
									"fees_category": trans_student.fee_category,
									"amount": trans_student.fee_amount,
									"gross_amount": trans_student.fee_amount
								})
								fee.taxes_and_charges = self.taxes_and_charges
								fee.taxes = self.taxes
								if self.receivable_account:
									fee.receivable_account = self.receivable_account
								if self.income_account:
									fee.income_account = self.income_account
								fee.save()
								# if trans_student.fee_category not in fees_category_array:
								#     row = self.append('components', {})
								#     row.fees_category = trans_student.fee_category
								#     row.amount = trans_student.fee_amount
								#     row.gross_amount = trans_student.fee_amount
								# else:
								#     for comp in self.components:
								#         if comp.fees_category == trans_student.fee_category:
								#             comp.amount = trans_student.fee_amount
								#             comp.gross_amount = trans_st
								created_records += 1
								frappe.publish_progress(created_records, title="Progress")
					except Exception as e:
						error = True
						err_msg = (
							frappe.local.message_log and "\n\n".join(
								frappe.local.message_log) or cstr(e)
						)
		else:
			frappe.throw("There are no transportation fee structure")
		if error:
			frappe.db.rollback()
			frappe.db.set_value("Transportation Fee Schedule", self.name,
								"fee_creation_status", "Failed")
			frappe.db.set_value("Transportation Fee Schedule", self.name, "error_log", err_msg)

		else:
			frappe.db.set_value("Transportation Fee Schedule", self.name,
								"fee_creation_status", "Successful")
			frappe.db.set_value("Transportation Fee Schedule", self.name, "error_log", None)

		frappe.publish_realtime(
			"transportation_fee_progress", {"progress": "100", "reload": 1}, user=frappe.session.user
		)
			

	@frappe.whitelist()
	def get_transportation_student_count(self):
		students = frappe.db.count("Student", filters=[
			["transportation_fee_structure", "Is", "Set"]
		])

		return students
	
	# def append_transportation(self):
    #     fee_student = frappe.get_doc('Student', self.student)
    #     if fee_student.transportation_fee_structure:
    #         trans_student = frappe.get_doc(
    #             'Transportation Fee Structure', fee_student.transportation_fee_structure, fields=['*'])
    #         fees_category_array = []
    #         stu_months_array = []
    #         tran_months_array = []

    #         for comp in self.components:
    #             fees_category_array.append(comp.fees_category)

    #         for m in fee_student.transportation_fee_structure_months:
    #             stu_months_array.append(m.month_number)

    #         for m in trans_student.transportation_fee_structure_months:
    #             tran_months_array.append(m.month_number)
                
    #         posting_month = frappe.utils.formatdate(self.posting_date, "MM")
    #         if frappe.utils.getdate(str(self.posting_date)) >= frappe.utils.getdate(str(fee_student.start_date)):
    #             if posting_month in stu_months_array or posting_month not in tran_months_array:
    #                 for comp in self.components:
    #                     if comp.fees_category == trans_student.fee_category:
    #                         self.components.remove(comp)
    #             elif (posting_month in tran_months_array 
    #                     and trans_student.dependant_fee_category in fees_category_array):
    #                     pass
    #                     # if trans_student.fee_category not in fees_category_array:
    #                     #     row = self.append('components', {})
    #                     #     row.fees_category = trans_student.fee_category
    #                     #     row.amount = trans_student.fee_amount
    #                     #     row.gross_amount = trans_student.fee_amount
    #                     # else:
    #                     #     for comp in self.components:
    #                     #         if comp.fees_category == trans_student.fee_category:
    #                     #             comp.amount = trans_student.fee_amount
    #                     #             comp.gross_amount = trans_student.fee_amount
    #                     # trans_fee = frappe.new_doc("Fees")
    #                     # trans_fee.student = self.student
    #                     # trans_fee.posting_date = self.posting_date
    #                     # trans_fee.due_date = self.due_date

    #                     # trans_fee.student_name = self.student_name
    #                     # trans_fee.program = self.program
    #                     # trans_fee.student_batch = self.student_batch
    #                     # # trans_fee.send_payment_request = self.send_payment_request
    #                     # trans_fee.components = []
    #                     # trans_fee.append('components', {
    #                     #     "fees_category": trans_student.fee_category,
    #                     #     "amount": trans_student.fee_amount,
    #                     #     "gross_amount": trans_student.fee_amount
    #                     # })
    #                     # trans_fee.taxes_and_charges = self.taxes_and_charges
                        
    #                     # # trans_fee.validate()
    #                     # trans_fee.save()
