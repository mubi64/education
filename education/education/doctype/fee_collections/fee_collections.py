# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from functools import reduce
from education.education.utils import round_val

import erpnext
import frappe
from frappe import _, scrub
from frappe.model.document import Document
from frappe.utils import now
import datetime

# from education.education.api import get_student_fee_details, get_student_fee_details_not_submit
from erpnext.accounts.doctype.payment_entry.payment_entry import set_party_type, set_party_account, set_party_account_currency, set_payment_type, set_grand_total_and_outstanding_amount, set_paid_amount_and_received_amount, apply_early_payment_discount, get_reference_as_per_payment_terms, update_accounting_dimensions, split_early_payment_discount_loss, set_pending_discount_loss, get_bank_cash_account
from frappe.utils import flt, getdate, nowdate, formatdate
from erpnext.accounts.doctype.bank_account.bank_account import get_party_bank_account
from education.education.doctype.fees.fees import get_student_dicount, check_duplicate_fees_batch, _post_fee_ledger

class FeeCollections(Document):
	def before_save(self):
		self.apply_discounts()

	def on_cancel(self):
		for fee in self.student_fee_details:
			if fee.fees:
				feedoc = frappe.get_doc("Fees", fee.fees)
				if feedoc.docstatus == 1:
					feedoc.cancel()

		
				
	@frappe.whitelist()
	def apply_discounts(self):
		if self.is_return == 0:
			if self.discount_type != "":
				for i, fee in enumerate(self.student_fee_details):
					cr_fee = frappe.get_doc("Fees", fee.fees)
					if cr_fee.docstatus != 1:
						cr_fee.update({
							"discount_type": self.discount_type,
							"discount_amount": self.discount_amount,
							"percentage": self.percentage,
							"fee_expense_account": self.fee_expense_account
						})
						cr_fee.total_discount_amount = flt(cr_fee.amount_before_discount) - flt(cr_fee.grand_total_before_tax)
						cr_fee.save()
					elif self.discount_type != "":
						frappe.throw(_("Not allowed to change any fields after submission at row  " + str(i +1)))
			
			self.advance_fee_discount()
		self.update_student_table()
		
	def update_student_table(self):
		fee_name_list = [fee.fees for fee in self.student_fee_details]

		fee_list = frappe.get_all("Fees", filters=[["name", "in", fee_name_list]], fields=["*"], order_by="student_name asc")
		self.student_fee_details = []

		self.grand_total = 0
		self.grand_total_b_d = 0
		self.grand_total_b_tax = 0
		self.total_tax_a = 0
		self.total_d_a = 0
		self.net_total = 0
		self.discount = 0
		self.net_total_a_d = 0

		for fee in fee_list:
			row = self.append('student_fee_details', {})
			row.update({
				'fees': fee.name,
				'student_id': fee.student,
				'student_name': fee.student_name,
				'discount_type': fee.discount_type,
				'discount_amount': fee.discount_amount,
				'percentage': fee.percentage,
				'amount_before_discount': fee.amount_before_discount,
				'due_date': fee.due_date,
				'posting_date': fee.posting_date,
				'grand_total_before_tax': fee.grand_total_before_tax,
				'total_amount': fee.grand_total,
				'total_taxes_and_charges': fee.total_taxes_and_charges,
				'outstanding_amount': fee.outstanding_amount,
				'allocated_amount': fee.outstanding_amount,
				'month': formatdate(fee.posting_date, "MMMM-yyyy"),
				'is_return': fee.is_return
			})

			compoArray = []
			components = frappe.db.get_values("Fee Component", filters={'parent': fee.name}, fieldname=['fees_category', 'gross_amount', 'amount'], as_dict=1)
			
			for fee_com in components:
				compoArray.append(fee_com.fees_category)
				dis_amount = flt(fee_com.gross_amount) - flt(fee_com.amount)
				self.net_total += fee_com.gross_amount
				self.discount += dis_amount
				self.net_total_a_d += fee_com.amount

			row.components = ", ".join(compoArray)
			
			
			self.grand_total += (round_val(fee.outstanding_amount, 4) if self.is_return == 0 else round(fee.grand_total, 4))
			self.grand_total_b_tax += round_val(fee.grand_total_before_tax, 4)
			self.total_tax_a += round_val(fee.total_taxes_and_charges, 4)
			self.grand_total_b_d += round_val(fee.amount_before_discount, 4)
			self.total_d_a += round_val(fee.total_discount_amount, 4)

		# Keep the payment amount in step with the total recalculated above.
		# The client script only sets it while fee rows are edited in the
		# browser, so when the underlying fees change afterwards (a discount
		# gets applied, a fee is edited or partly paid) grand_total moves here
		# while the payment row keeps its old figure - which then fails
		# validate_amounts() on submit with no indication of why.
		#
		# Only done for a single payment row: a deliberate split across two
		# modes of payment must not be overwritten. And only when there is
		# actually something left to collect - if every fee on this receipt has
		# since been paid through another one, grand_total is 0, and syncing
		# would quietly turn this into a zero-value receipt that submits
		# cleanly; leaving the amount alone keeps validate_amounts() refusing it.
		if len(self.fee_collection_payment) == 1 and self.grand_total:
			self.fee_collection_payment[0].amount = self.grand_total

	
	def advance_fee_discount(self):
		advance_fee = []
		edu_settings = frappe.get_doc("Education Settings")

		if edu_settings.enable_discount == 1:
			student_count = {}
			allowed_categories = [category.student_category for category in edu_settings.applicable_student_categories]
			student_ids = [fee.student_id for fee in self.student_fee_details]

			students = frappe.get_all("Student", filters=[
				["name", "in", student_ids],
				["student_category", "in", allowed_categories]
			])
			allowed_student_names = {student["name"] for student in students}

			apply_discount_fees = [fee for fee in self.student_fee_details if fee.student_id in allowed_student_names]
			
			total_discount_amount = 0
			for fee in apply_discount_fees:
				student = fee.student_id
				if str(fee.due_date) >= now():
					student_count[student] = student_count.get(student,0) + 1
			for fee in apply_discount_fees:
				# Check eligibility for discount
				if str(fee.due_date) >= now():
					student_id = fee.student_id

					for dis_slab in edu_settings.discount_slabs:
						due_date_condition = str(fee.due_date) >= now()
						discount_component_condition = edu_settings.apply_discount_on in fee.components
						
						if (dis_slab.from_month <= student_count[student_id] <= dis_slab.to_month 
							and due_date_condition and discount_component_condition):
							advance_fee.append(fee)

			for dis_slab in edu_settings.discount_slabs:
				if dis_slab.from_month <= len(advance_fee) <= dis_slab.to_month:
					for adv_fee in advance_fee:
						fee = frappe.get_doc("Fees", adv_fee.fees)
						fee.discount_type = dis_slab.discount_type

						if dis_slab.discount_type == "Percentage":
							fee.percentage = dis_slab.percentage
						elif dis_slab.discount_type == "Amount":
							fee.discount_amount = dis_slab.amount

						fee.fee_expense_account = edu_settings.discount_expense_account
						fee.save()
						total_discount_amount += fee.total_discount_amount
				else:
					for adv_fee in advance_fee:
						fee = frappe.get_doc("Fees", adv_fee.fees)
						if fee.discount_type != "":
							fee.discount_type = ""
							fee.percentage = 0
							fee.discount_amount = 0
							fee.save()
				
				remove_discount_fees = [item for item in self.student_fee_details if item not in advance_fee]

				for adv_fee in remove_discount_fees:
					fee = frappe.get_doc("Fees", adv_fee.fees)
					if fee.discount_type != "":
						fee.discount_type = ""
						fee.percentage = 0
						fee.discount_amount = 0
						fee.save()
			self.total_d_a = total_discount_amount


	def on_submit(self):
		self.validate_amounts()

		if self.is_return == 1:
			for item in self.student_fee_details:
				fee_doc = frappe.get_doc("Fees", item.fees, fields=['*'])

				if fee_doc.outstanding_amount == 0:
					frappe.db.set_value("Fees", fee_doc.name, "is_return", 1)
					self.create_journal_entry(fee_doc)

		else:
			pending_fees = []
			for item in self.student_fee_details:
				current_fee = frappe.get_doc("Fees", item.fees)
				if current_fee.docstatus != 1:
					pending_fees.append(current_fee)

			if pending_fees:
				# Check every pending fee for duplicates in one pass, before
				# saving any of them - same rule as before, just asked once
				# per student+month instead of once per fee item.
				check_duplicate_fees_batch(pending_fees)

				company_defaults = {}
				discount_docs = {}
				student_emails = {}

				for current_fee in pending_fees:
					if not current_fee.company:
						current_fee.company = frappe.defaults.get_defaults().company
					company = current_fee.company

					if company not in company_defaults:
						accounts_details = frappe.get_all(
							"Company",
							fields=["default_receivable_account", "default_income_account", "cost_center"],
							filters={"name": company},
						)[0]
						company_defaults[company] = {
							"currency": erpnext.get_company_currency(company),
							"receivable_account": accounts_details.default_receivable_account,
							"income_account": accounts_details.default_income_account,
							"cost_center": accounts_details.cost_center,
						}
					defaults = company_defaults[company]

					if not current_fee.currency:
						current_fee.currency = defaults["currency"]
					if not current_fee.receivable_account:
						current_fee.receivable_account = defaults["receivable_account"]
					if not current_fee.income_account:
						current_fee.income_account = defaults["income_account"]
					if not current_fee.cost_center:
						current_fee.cost_center = defaults["cost_center"]

					student = current_fee.student
					if student not in discount_docs:
						discount_docs[student] = get_student_dicount(student)
					if student not in student_emails:
						student_emails[student] = current_fee.get_student_emails()
					if not current_fee.student_email:
						current_fee.student_email = student_emails[student]

					current_fee.flags.skip_duplicate_check = True
					current_fee.flags.cached_discount_doc = discount_docs[student]
					current_fee.flags.defer_gl_posting_to_caller = True

					current_fee.fee_collections = self.name
					current_fee.save()
					current_fee.submit()

			# The Payment Entry (below, in create_payment_entries) has to be
			# created *after* every fee item's own ledger entry is posted -
			# otherwise its credit-side entry could land before the fee's
			# own debit-side entry exists, and the fee's Outstanding Amount
			# would briefly read wrong. So both steps happen together in one
			# background job, in that order, instead of here.
			frappe.enqueue(
				method="education.education.doctype.fee_collections.fee_collections.post_fee_collection_ledger_entries",
				queue="short",
				enqueue_after_commit=True,
				fee_collection_name=self.name,
			)

	def create_payment_entries(self):
		posted_fees = {
			item.fees for item in self.student_fee_details
			if frappe.db.get_value("Fees", item.fees, "gl_posting_status") == "Posted"
		}

		# The receipt's own stored outstanding_amount (item.outstanding_amount,
		# a snapshot taken when the receipt was drafted) can go stale if the
		# fee itself changed afterwards - and ERPNext's own Payment Entry
		# validation always force-refreshes each reference's outstanding
		# amount from the fee's CURRENT value on submit
		# (set_missing_ref_details(force=True) in payment_entry.py),
		# regardless of what we set here. Allocating against the stale
		# snapshot can then end up allocating more than the fee's current
		# outstanding amount, failing with "Allocated Amount cannot be
		# greater than outstanding amount". Fetch each posted fee's live
		# amount once, up front, and allocate against that instead.
		live_outstanding = {}
		if posted_fees:
			for f in frappe.get_all(
				"Fees",
				filters={"name": ["in", list(posted_fees)]},
				fields=["name", "outstanding_amount", "grand_total"],
			):
				live_outstanding[f.name] = min(flt(f.outstanding_amount), flt(f.grand_total))

		# Payment Entry compares its received amount against the SUM of
		# each reference's allocated amount rounded independently to
		# base_paid_amount's precision (2 decimals here) - not the
		# precision allocated_amount is stored at (3). With several fee
		# items in one receipt, rounding each item's share to 3 decimals
		# and summing can land a fraction of a halala away from what a
		# single 2-decimal rounding of the total gives, which is exactly
		# what trips ERPNext's "Difference Amount must be zero" check on
		# submit. Rounding to that same 2-decimal precision here, with
		# the last item absorbing the remainder, guarantees the sum
		# always matches exactly.
		difference_precision = frappe.get_precision("Payment Entry", "base_paid_amount")

		for row in self.fee_collection_payment:
			amount_percentage = row.amount / self.grand_total * 100
			self.mode_of_payment = row.mode_of_payment

			# One Payment Entry can only have one party, so allocations are grouped
			# by student first - a collection can cover multiple siblings at once -
			# and every fee item for that same student is combined into a single
			# Payment Entry instead of one per fee item.
			allocations_by_student = {}
			for item in self.student_fee_details:
				if item.fees not in posted_fees:
					# That fee's own ledger entry failed to post - skip it
					# rather than allocate payment against a fee with no
					# ledger entry to reference. Left for manual follow-up
					# (see the Error Log entry from the failed posting).
					continue
				live_amount = live_outstanding.get(item.fees, 0)
				outst_amount = live_amount / 100 * amount_percentage
				allocations_by_student.setdefault(item.student_id, []).append((item, outst_amount, live_amount))

			for student_id, raw_allocations in allocations_by_student.items():
				total_allocated = round_val(sum(outst for _, outst, _ in raw_allocations), difference_precision)
				running_total = 0
				allocations = []
				for idx, (item, outst_amount, live_amount) in enumerate(raw_allocations):
					if idx == len(raw_allocations) - 1:
						allocated = round_val(total_allocated - running_total, difference_precision)
					else:
						allocated = round_val(outst_amount, difference_precision)
						running_total += allocated
					# Never allocate more than what's genuinely still owed on
					# this fee right now, even after remainder-absorption -
					# guards against the same kind of staleness that caused
					# the allocation math itself to overshoot.
					allocated = min(allocated, live_amount)
					allocations.append((item, allocated, live_amount))

				total_allocated = round_val(sum(a for _, a, _ in allocations), difference_precision)
				if total_allocated <= 0:
					# Everything in this group is already fully paid - nothing
					# left to create a Payment Entry for.
					continue

				first_item, _, _ = allocations[0]
				temp_dict = {
					"name": student_id,
					"amount": total_allocated,
					"fee": first_item.fees
				}
				values = self.get_payment_entry("Fees", temp_dict["fee"], temp_dict, party_type="Student", payment_type="Receive")
				values.reference_no = self.reference_no
				values.reference_date = self.reference_date

				values.references = []
				for item, allocated, live_amount in allocations:
					values.append("references", {
						"reference_doctype": "Fees",
						"reference_name": item.fees,
						"total_amount": live_amount,
						"outstanding_amount": live_amount,
						"allocated_amount": allocated,
					})

				values.insert()
				values.submit()


	def validate_amounts(self):
		amount_in_table = sum(round_val(row.amount, 4) for row in self.fee_collection_payment)
		amount_in_fee_table = sum(round_val(row.outstanding_amount, 4) for row in self.student_fee_details) if self.is_return == 0 else sum(round_val(row.total_amount, 4) for row in self.student_fee_details)

		# print(amount_in_table, amount_in_fee_table, "amount_in_table, amount_in_fee_table \n\n\n\n\n")
		# print(round_val(amount_in_table, 4), round_val(amount_in_fee_table, 4), "round_val(amount_in_table, 4), round_val(amount_in_fee_table, 4) \n\n\n\n\n")
		if round_val(amount_in_table, 4) != round_val(amount_in_fee_table, 4):
			frappe.throw(_("Amount must be equal to grand total. Payment amount is {0} but the fee items total {1} (difference {2}). Clear the Amount field and re-enter it to pick up the current total.").format(
				round_val(amount_in_table, 4),
				round_val(amount_in_fee_table, 4),
				round_val(amount_in_table - amount_in_fee_table, 4),
			))

	def create_journal_entry(self, fee_doc):
		from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account

		journal_entry = frappe.get_doc({
			"doctype": "Journal Entry",
			"posting_date": now(),
			# "title": fee_doc.name,
			"accounts": [],
		})

		for com in fee_doc.components:
			incom_acc = frappe.get_doc("Fee Category", com.fees_category)
			journal_entry.append("accounts", {
				"account": incom_acc.income_account,
				"debit_in_account_currency": com.amount,
				"reference_type": "Fees",
				"reference_name": fee_doc.name
			})

		for tax in fee_doc.taxes:
			journal_entry.append("accounts", {
				"account": tax.account_head,
				"debit_in_account_currency": tax.tax_amount,
				"reference_type": "Fees",
				"reference_name": fee_doc.name
			})

		if fee_doc.discount_type != "":
			journal_entry.append("accounts", {
				"account": fee_doc.fee_expense_account,
				"credit_in_account_currency": fee_doc.total_discount_amount,
				"reference_type": "Fees",
				"reference_name": fee_doc.name
			})

		for row in self.fee_collection_payment:
			amount_percentage = 0
			outst_amount = 0
			amount_percentage = flt(row.amount) / flt(self.grand_total) * 100
			outst_amount = flt(fee_doc.grand_total) / 100 * flt(amount_percentage)
			credit_account = get_bank_cash_account(row.mode_of_payment, self.company)
			
			journal_entry.append("accounts", {
				"account": credit_account.get('account'),
				"credit_in_account_currency": outst_amount, # grand_total_before_tax,
				"reference_type": "Fees",
				"reference_name": fee_doc.name
			})

		journal_entry.insert()
		journal_entry.submit()


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
		# print(party_account, payment_type, bank.account, pe.paid_from, "Check Account \n\n\n\n\n\n\n\n\n")
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
						if fee["fee"] == student_fee.fees:
							pe.append(
								"references",
								{
									"reference_doctype": dt,
									"reference_name": student_fee.fees,
									"bill_no": doc.get("bill_no"),
									"due_date": doc.get("due_date"),
									"total_amount": student_fee.outstanding_amount,
									"outstanding_amount": student_fee.outstanding_amount,
									"allocated_amount": fee["amount"],
								},
							)

					# for reference in pe.get("references", []):
					# 	print(outstanding_amount, "outstanding_amount")
					# 	print(reference.total_amount)
					# 	print(reference.outstanding_amount)
					# 	print(reference.allocated_amount)
					# 	print(reference, "reference \n\n\n\n\n")

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


def post_fee_collection_ledger_entries(fee_collection_name):
	"""Background job for one Fee Collections submission.

	Posts each of its pending Fees documents' own ledger entries first
	(still one at a time, still separate GL/Payment Ledger entries per fee -
	unchanged from the original synchronous code), and only once that's
	done, creates the consolidated Payment Entry per student. Doing it in
	this order avoids a window where a Payment Entry's credit-side entry
	would exist before the matching Fees document's own debit-side entry.
	"""
	fee_collection = frappe.get_doc("Fee Collections", fee_collection_name)

	for item in fee_collection.student_fee_details:
		fee_doc = frappe.get_doc("Fees", item.fees)
		if fee_doc.docstatus == 1 and fee_doc.gl_posting_status != "Posted":
			_post_fee_ledger(fee_doc)

	try:
		fee_collection.create_payment_entries()
	except Exception:
		frappe.db.rollback()
		frappe.log_error(title=f"Fee Collections {fee_collection_name}: payment entry creation failed")
		frappe.db.commit()


