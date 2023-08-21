# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from functools import reduce

import frappe
from frappe import _, scrub
from frappe.model.document import Document

from education.education.api import get_student_fee_details, get_student_fee_details_not_submit
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry, set_party_type, set_party_account, set_party_account_currency, set_payment_type, set_grand_total_and_outstanding_amount, set_paid_amount_and_received_amount, apply_early_payment_discount, get_reference_as_per_payment_terms, update_accounting_dimensions, split_early_payment_discount_loss, set_pending_discount_loss, get_bank_cash_account
from frappe.utils import flt, getdate, nowdate
from erpnext.accounts.doctype.bank_account.bank_account import (
	get_party_bank_account,
)



class FeeCollections(Document):

	def before_save(self):
		for i, fee in enumerate(self.student_fee_details):
			cr_fee = frappe.get_doc("Fees", fee.fees)
			if cr_fee.docstatus != 1:
				cr_fee.discount_type = self.discount_type
				cr_fee.discount_amount = self.discount_amount
				cr_fee.percentage = self.percentage
				cr_fee.fee_expense_account = self.fee_expense_account
				cr_fee.save()
				cr_fee.total_discount_amount = cr_fee.amount_before_discount - cr_fee.grand_total_before_tax
				cr_fee.save()
			elif self.discount_type != "":
				frappe.throw(_("Not allowed to change any fields after submission at row  " + str(i +1)))
		if self.discount_type != "":
			self.update_student_table()

		
	def update_student_table(self):
		if self.student:
			fee_list = []
			if self.discount_type == "":
				fee_list = get_student_fee_details(self.student, None)
			else:
				fee_list = get_student_fee_details_not_submit(self.student, None)
			self.student_fee_details = []
			for fee in fee_list:
				row = self.append('student_fee_details', {})
				row.fees = fee.name
				row.student_id = fee.student
				row.student_name = fee.student_name
				row.discount_type = fee.discount_type
				row.discount_amount = fee.discount_amount
				row.percentage = fee.percentage
				row.amount_before_discount = fee.amount_before_discount
				row.due_date = fee.due_date
				row.grand_total_before_tax = fee.grand_total_before_tax
				row.total_amount = fee.grand_total
				row.total_taxes_and_charges = fee.total_taxes_and_charges
				row.outstanding_amount = fee.outstanding_amount
				row.allocated_amount = fee.outstanding_amount
		
		if self.family_code:
			fee_list= []
			if self.discount_type == "":
				fee_list = get_student_fee_details(self.student, None)
			else:
				fee_list = get_student_fee_details_not_submit(self.student, None)
			self.student_fee_details = []
			for fee in fee_list:
				row = self.append('student_fee_details', {})
				row.fees = fee.name
				row.student_id = fee.student
				row.student_name = fee.student_name
				row.discount_type = fee.discount_type
				row.discount_amount = fee.discount_amount
				row.percentage = fee.percentage
				row.amount_before_discount = fee.amount_before_discount
				row.due_date = fee.due_date
				row.grand_total_before_tax = fee.grand_total_before_tax
				row.total_amount = fee.grand_total
				row.total_taxes_and_charges = fee.total_taxes_and_charges
				row.outstanding_amount = fee.outstanding_amount
				row.allocated_amount = fee.outstanding_amount

	def on_submit(self):
		# if self.discount_type != None:
		# 	print("heeelo World 7")
		# 	self.apply_discount()
		# # self.make_payment_entry()
		student_fees = []
		temp_dict = {}

		for item in self.student_fee_details:
			current_fee = frappe.get_doc("Fees", item.fees)
			if current_fee.docstatus != 1:
				current_fee.save()
				current_fee.submit()
			name = item.student_id
			if name not in temp_dict:
				temp_dict[name] = {"name": name, "amount": 0, "fee": ""}
			
			temp_dict[name]["amount"] += item.outstanding_amount
			if item.student_id == temp_dict[name]["name"]: 
				temp_dict[name]["fee"] = item.fees

		student_fees = list(temp_dict.values())

		for fee in student_fees:
			values = self.get_payment_entry("Fees", fee["fee"], fee, party_type="Student", payment_type="Receive")
			values.insert()
			values.submit()
			

	# def apply_discount(self):
	# 	for fee in self.student_fee_details:
	# 		current_fee = frappe.get_doc("Fees", fee.fees)
	# 		current_fee.fee_expense_account = self.fee_expense_account
	# 		if self.discount_type == "Percentage" and current_fee.discount_type == "Percentage":
	# 			current_fee.percentage += self.percentage
				
	# 		# if current_fee.discount_type == "Amount":
	# 		# 	frappe.throw(_('Discount Type not match'))
	# 		# else:
	# 		# 	current_fee.discount_type = "Percentage"
	# 		# 	current_fee.percentage += self.percentage

		
	# 		elif self.discount_type == "Amount" and current_fee.discount_type == "Amount":
	# 			current_fee.discount_amount += self.discount_amount
	# 		# if current_fee.discount_type == "Percentage":
	# 		# 	frappe.throw(_('Discount Type not match'))
	# 		# else:
	# 		# 	current_fee.discount_type = "Amount"
	# 		# 	current_fee.discount_amount += self.discount_amount

	# 		elif self.discount_type != "" and current_fee.discount_type == "":
	# 			current_fee.discount_type = self.discount_type
	# 			current_fee.discount_amount = self.discount_amount
	# 			current_fee.percentage = self.percentage


	# 		current_fee.save()
	# 		current_fee.submit()

		

	# def make_payment_entry(self):
		# combined_data = {}

		# for entry in self.student_fee_details:
		# 	name = entry.student_id
		# 	amount = entry.outstanding_amount
		# 	if name in combined_data:
		# 		combined_data[name] += amount
		# 	else:
		# 		combined_data[name] = amount

		# student_fee = [{"name": name, "amount": amount} for name, amount in combined_data.items()]

	# 	student_fees = []
	# 	temp_dict = {}

	# 	for item in self.student_fee_details:
	# 		name = item.student_id
	# 		if name not in temp_dict:
	# 			temp_dict[name] = {"name": name, "amount": 0, "fee": ""}
			
	# 		temp_dict[name]["amount"] += item.outstanding_amount
	# 		print(item.student_id == temp_dict[name]["name"], item.student_id , temp_dict[name]["name"], "checking name list")
	# 		if item.student_id == temp_dict[name]["name"]: 
	# 			temp_dict[name]["fee"] = item.fees

	# 	student_fees = list(temp_dict.values())

	# 	print(student_fees, "Fees Checking")

	# 	for fee in student_fees:
	# 		doc = get_payment_entry("Fees", fee["fee"], party_type="Student", payment_type="Receive")
	# 		doc.paid_amount = fee["amount"]
	# 		# for student_fee in self.student_fee_details:
	# 		# 	doc.append("references", {
	# 		# 		"reference_doctype": "Fees",
	# 		# 		"reference_name": student_fee.fees,
	# 		# 		"allocated_amount": student_fee.outstanding_amount,
	# 		# 	})
	# 		doc.mode_of_payment = self.mode_of_payment
	# 		doc.total_allocated_amount = fee["amount"]
	# 		doc.paid_to = get_bank_cash_account(self.mode_of_payment, self.company).get("account")
			
	# 		print(doc.target_exchange_rate, "Print")
	# 		print(doc.paid_to, "doc.paid_to")
	# 		# doc.setup_party_account_field()
	# 		# doc.set_missing_values()
	# 		# doc.set_missing_ref_details()
	# 		doc.set_exchange_rate()
	# 		# doc.set_amounts()
	# 		# doc.set_difference_amount()
	# 		# doc.validate()
	# 		doc.insert()
	# 		# payment = frappe.new_doc("Payment Entry")
	# 		# payment.mode_of_payment =  self.mode_of_payment
	# 		# payment.party_type = "Student"
	# 		# payment.party =  fee["name"]
	# 		# payment.payment_type = "Receive"
	# 		# payment.paid_amount =  fee["amount"]
	# 		# payment.received_amount =  fee["amount"]
	# 		# row = payment.append("references", {})
	# 		# for category_fee in self.student_fee_details:
	# 		# 	row.reference_doctype = "Fees"
	# 		# 	row.reference_name = category_fee.fees
	# 		# 	row.grand_total = category_fee.outstanding_amount
	# 		# 	row.outstanding_amount = category_fee.outstanding_amount
	# 		# 	row.allocated_amount = category_fee.outstanding_amount


	# 		# print(payment.party_type, "Check payment entry")

	# 		# payment.setup_party_account_field()
	# 		# payment.set_missing_values()
	# 		# payment.set_missing_ref_details()
	# 		# payment.insert()

	def get_payment_entry(
		self,
		dt,
		dn,
		fee,
		party_amount=None,
		bank_account=None,
		bank_amount=None,
		party_type=None,
		payment_type=None,
		reference_date=None,
	):
		reference_doc = None
		doc = frappe.get_doc(dt, dn)
		over_billing_allowance = frappe.db.get_single_value("Accounts Settings", "over_billing_allowance")
		if dt in ("Sales Order", "Purchase Order") and flt(doc.per_billed, 2) >= (
			100.0 + over_billing_allowance
		):
			frappe.throw(_("Can only make payment against unbilled {0}").format(dt))

		if not party_type:
			party_type = set_party_type(dt)

		party_account = set_party_account(dt, dn, doc, party_type)
		party_account_currency = set_party_account_currency(dt, party_account, doc)

		if not payment_type:
			payment_type = set_payment_type(dt, doc)

		grand_total, outstanding_amount = set_grand_total_and_outstanding_amount(
			party_amount, dt, party_account_currency, doc
		)

		# bank or cash
		print(self, "Vlues cheking")
		bank = get_bank_cash_account(self, bank_account)

		# if default bank or cash account is not set in company master and party has default company bank account, fetch it
		if party_type in ["Customer", "Supplier"] and not bank:
			party_bank_account = get_party_bank_account(party_type, doc.get(scrub(party_type)))
			if party_bank_account:
				account = frappe.db.get_value("Bank Account", party_bank_account, "account")
				bank = get_bank_cash_account(self, account)

		paid_amount, received_amount = set_paid_amount_and_received_amount(
			dt, party_account_currency, bank, outstanding_amount, payment_type, bank_amount, doc
		)

		reference_date = getdate(reference_date)
		paid_amount, received_amount, discount_amount, valid_discounts = apply_early_payment_discount(
			paid_amount, received_amount, doc, party_account_currency, reference_date
		)

		pe = frappe.new_doc("Payment Entry")
		pe.payment_type = payment_type
		pe.company = doc.company
		pe.cost_center = doc.get("cost_center")
		pe.posting_date = nowdate()
		pe.reference_date = reference_date
		pe.mode_of_payment = self.get("mode_of_payment")
		pe.party_type = party_type
		pe.party = doc.get(scrub(party_type))
		pe.contact_person = doc.get("contact_person")
		pe.contact_email = doc.get("contact_email")
		pe.ensure_supplier_is_not_blocked()

		pe.paid_from = party_account if payment_type == "Receive" else bank.account
		pe.paid_to = party_account if payment_type == "Pay" else bank.account
		pe.paid_from_account_currency = (
			party_account_currency if payment_type == "Receive" else bank.account_currency
		)
		pe.paid_to_account_currency = (
			party_account_currency if payment_type == "Pay" else bank.account_currency
		)
		pe.paid_amount = fee["amount"]
		pe.received_amount = fee["amount"]
		pe.letter_head = doc.get("letter_head")

		if dt in ["Purchase Order", "Sales Order", "Sales Invoice", "Purchase Invoice"]:
			pe.project = doc.get("project") or reduce(
				lambda prev, cur: prev or cur, [x.get("project") for x in doc.get("items")], None
			)  # get first non-empty project from items

		if pe.party_type in ["Customer", "Supplier"]:
			bank_account = get_party_bank_account(pe.party_type, pe.party)
			pe.set("bank_account", bank_account)
			pe.set_bank_account_data()

		# only Purchase Invoice can be blocked individually
		if doc.doctype == "Purchase Invoice" and doc.invoice_is_blocked():
			frappe.msgprint(_("{0} is on hold till {1}").format(doc.name, doc.release_date))
		else:
			if doc.doctype in (
				"Sales Invoice",
				"Purchase Invoice",
				"Purchase Order",
				"Sales Order",
			) and frappe.get_cached_value(
				"Payment Terms Template",
				{"name": doc.payment_terms_template},
				"allocate_payment_based_on_payment_terms",
			):

				for reference in get_reference_as_per_payment_terms(
					doc.payment_schedule, dt, dn, doc, grand_total, outstanding_amount, party_account_currency
				):
					pe.append("references", reference)
			else:
				if dt == "Dunning":
					pe.append(
						"references",
						{
							"reference_doctype": "Sales Invoice",
							"reference_name": doc.get("sales_invoice"),
							"bill_no": doc.get("bill_no"),
							"due_date": doc.get("due_date"),
							"total_amount": doc.get("outstanding_amount"),
							"outstanding_amount": doc.get("outstanding_amount"),
							"allocated_amount": doc.get("outstanding_amount"),
						},
					)
					pe.append(
						"references",
						{
							"reference_doctype": dt,
							"reference_name": dn,
							"bill_no": doc.get("bill_no"),
							"due_date": doc.get("due_date"),
							"total_amount": doc.get("dunning_amount"),
							"outstanding_amount": doc.get("dunning_amount"),
							"allocated_amount": doc.get("dunning_amount"),
						},
					)
				else:
					for student_fee in self.student_fee_details:
						# doc.append("references", {
						# 	"reference_doctype": "Fees",
						# 	"reference_name": student_fee.fees,
						# 	"allocated_amount": student_fee.outstanding_amount,
						# })
						if fee["name"] == student_fee.student_id:
							pe.append(
								"references",
								{
									"reference_doctype": dt,
									"reference_name": student_fee.fees,
									"bill_no": doc.get("bill_no"),
									"due_date": doc.get("due_date"),
									"total_amount": grand_total,
									"outstanding_amount": student_fee.outstanding_amount,
									"allocated_amount": student_fee.outstanding_amount,
								},
							)

		pe.setup_party_account_field()
		pe.set_missing_values()
		pe.set_missing_ref_details()

		update_accounting_dimensions(pe, doc)

		if party_account and bank:
			pe.set_exchange_rate(ref_doc=reference_doc)
			pe.set_amounts()

			if discount_amount:
				base_total_discount_loss = 0
				if frappe.db.get_single_value("Accounts Settings", "book_tax_discount_loss"):
					base_total_discount_loss = split_early_payment_discount_loss(pe, doc, valid_discounts)

				set_pending_discount_loss(
					pe, doc, discount_amount, base_total_discount_loss, party_account_currency
				)

			pe.set_difference_amount()

		return pe
