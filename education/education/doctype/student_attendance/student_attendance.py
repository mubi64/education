# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt


import frappe
from erpnext import get_default_company
from erpnext.setup.doctype.holiday_list.holiday_list import is_holiday
from frappe import _
from frappe.website.website_generator import WebsiteGenerator
from frappe.utils import formatdate, get_link_to_form, getdate

from education.education.api import get_student_group_students


class StudentAttendance(WebsiteGenerator):
	def validate(self):
		if not self.route:
			self.route = "attendance/" + self.name
		self.validate_mandatory()
		self.validate_date()
		self.set_date()
		self.set_student_group()
		self.validate_student()
		self.validate_duplication()
		self.validate_is_holiday()

	def set_date(self):
		if self.course_schedule:
			self.date = frappe.db.get_value(
				"Course Schedule", self.course_schedule, "schedule_date"
			)

	def validate_mandatory(self):
		if not (self.student_group or self.course_schedule):
			frappe.throw(
				_("{0} or {1} is mandatory").format(
					frappe.bold("Student Group"), frappe.bold("Course Schedule")
				),
				title=_("Mandatory Fields"),
			)

	def validate_date(self):
		if not self.leave_application and getdate(self.date) > getdate():
			frappe.throw(_("Attendance cannot be marked for future dates."))

		if self.student_group:
			academic_year = frappe.db.get_value(
				"Student Group", self.student_group, "academic_year"
			)
			if academic_year:
				year_start_date, year_end_date = frappe.db.get_value(
					"Academic Year", academic_year, ["year_start_date", "year_end_date"]
				)
				if year_start_date and year_end_date:
					if getdate(self.date) < getdate(year_start_date) or getdate(self.date) > getdate(
						year_end_date
					):
						frappe.throw(
							_("Attendance cannot be marked outside of Academic Year {0}").format(
								academic_year
							)
						)

	def set_student_group(self):
		if self.course_schedule:
			self.student_group = frappe.db.get_value(
				"Course Schedule", self.course_schedule, "student_group"
			)

	def validate_student(self):
		if self.course_schedule:
			student_group = frappe.db.get_value(
				"Course Schedule", self.course_schedule, "student_group"
			)
		else:
			student_group = self.student_group
		student_group_students = [
			d.student for d in get_student_group_students(student_group)
		]
		if student_group and self.student not in student_group_students:
			student_group_doc = get_link_to_form("Student Group", student_group)
			frappe.throw(
				_("Student {0}: {1} does not belong to Student Group {2}").format(
					frappe.bold(self.student), self.student_name, frappe.bold(student_group_doc)
				)
			)

	def validate_duplication(self):
		"""Check if the Attendance Record is Unique"""
		attendance_record = None
		if self.course_schedule:
			attendance_record = frappe.db.exists(
				"Student Attendance",
				{
					"student": self.student,
					"course_schedule": self.course_schedule,
					"docstatus": ("!=", 2),
					"name": ("!=", self.name),
				},
			)
		else:
			attendance_record = frappe.db.exists(
				"Student Attendance",
				{
					"student": self.student,
					"student_group": self.student_group,
					"date": self.date,
					"docstatus": ("!=", 2),
					"name": ("!=", self.name),
					"course_schedule": "",
				},
			)

		if attendance_record:
			record = get_link_to_form("Student Attendance", attendance_record)
			frappe.throw(
				_("Student Attendance record {0} already exists against the Student {1}").format(
					record, frappe.bold(self.student)
				),
				title=_("Duplicate Entry"),
			)

	def validate_is_holiday(self):
		holiday_list = get_holiday_list()
		if is_holiday(holiday_list, self.date):
			frappe.throw(
				_("Attendance cannot be marked for {0} as it is a holiday.").format(
					frappe.bold(formatdate(self.date))
				)
			)


def get_holiday_list(company=None):
	if not company:
		company = get_default_company() or frappe.get_all("Company")[0].name

	holiday_list = frappe.get_cached_value("Company", company, "default_holiday_list")
	if not holiday_list:
		frappe.throw(
			_("Please set a default Holiday List for Company {0}").format(
				frappe.bold(get_default_company())
			)
		)
	return holiday_list


def get_attendance_list(
        doctype, txt, filters, limit_start, limit_page_length=20, order_by="modified"
):
    user = frappe.session.user
    guardian = frappe.db.sql(
        "select family_code from `tabGuardian` where user= %s limit 1", user
    )
    if guardian:
        return frappe.db.sql(
            """
			select name, student, student_name, route, date, status, absent_fine_record
			from `tabStudent Attendance`
			where student in 
            (select name from `tabStudent` where family_code=%s) 
            and docstatus<>2
			order by date asc limit {0} , {1}""".format(
                limit_start, limit_page_length
            ),
            guardian,
            as_dict=True,
        )


def get_list_context(context=None):
    return {
        "show_sidebar": True,
        "show_search": True,
        "no_breadcrumbs": True,
        "title": _("Student Attendance"),
        "get_list": get_attendance_list,
        "row_template": "education/doctype/student_attendance/templates/student_attendance_row.html",
    }
