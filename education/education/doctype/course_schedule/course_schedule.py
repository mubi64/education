# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt


from datetime import datetime

import frappe
from frappe import _
from frappe.website.website_generator import WebsiteGenerator


class CourseSchedule(WebsiteGenerator):
	def validate(self):
		if not self.route:
			self.route = "timetable/" + self.name
		self.instructor_name = frappe.db.get_value(
			"Instructor", self.instructor, "instructor_name"
		)
		self.set_title()
		self.validate_course()
		self.validate_date()
		self.validate_time()
		self.validate_overlap()

	def set_title(self):
		"""Set document Title"""
		self.title = (
			self.course
			+ " by "
			+ (self.instructor_name if self.instructor_name else self.instructor)
		)

	def validate_course(self):
		group_based_on, course = frappe.db.get_value(
			"Student Group", self.student_group, ["group_based_on", "course"]
		)
		if group_based_on == "Course":
			self.course = course

	def validate_date(self):
		academic_year, academic_term = frappe.db.get_value(
			"Student Group", self.student_group, ["academic_year", "academic_term"]
		)
		self.schedule_date = frappe.utils.getdate(self.schedule_date)

		if academic_term:
			start_date, end_date = frappe.db.get_value(
				"Academic Term", academic_term, ["term_start_date", "term_end_date"]
			)
			if (
				start_date
				and end_date
				and (self.schedule_date < start_date or self.schedule_date > end_date)
			):
				frappe.throw(
					_(
						"Schedule date selected does not lie within the Academic Term of the Student Group {0}."
					).format(self.student_group)
				)

		elif academic_year:
			start_date, end_date = frappe.db.get_value(
				"Academic Year", academic_year, ["year_start_date", "year_end_date"]
			)
			if self.schedule_date < start_date or self.schedule_date > end_date:
				frappe.throw(
					_(
						"Schedule date selected does not lie within the Academic Year of the Student Group {0}."
					).format(self.student_group)
				)

	def validate_time(self):
		"""Validates if from_time is greater than to_time"""
		if self.from_time > self.to_time:
			frappe.throw(_("From Time cannot be greater than To Time."))

		"""Handles specicfic case to update schedule date in calendar """
		if isinstance(self.from_time, str):
			try:
				datetime_obj = datetime.strptime(self.from_time, "%Y-%m-%d %H:%M:%S")
				self.schedule_date = datetime_obj
			except ValueError:
				pass

	def validate_overlap(self):
		"""Validates overlap for Student Group, Instructor, Room"""

		from education.education.utils import validate_overlap_for

		# Validate overlapping course schedules.
		if self.student_group:
			validate_overlap_for(self, "Course Schedule", "student_group")

		validate_overlap_for(self, "Course Schedule", "instructor")
		validate_overlap_for(self, "Course Schedule", "room")

		# validate overlapping assessment schedules.
		if self.student_group:
			validate_overlap_for(self, "Assessment Plan", "student_group")

		validate_overlap_for(self, "Assessment Plan", "room")
		validate_overlap_for(self, "Assessment Plan", "supervisor", self.instructor)

def get_course_list(
        doctype, txt, filters, limit_start, limit_page_length=20, order_by="modified"
):
    user = frappe.session.user
    guardian = frappe.db.sql(
        "select family_code from `tabGuardian` where user= %s limit 1", user
    )
    if guardian:
        return frappe.db.sql(
            """
			select name, student_group, program, instructor, instructor_name, course, schedule_date, room, from_time, to_time, route
			from `tabCourse Schedule`
			where student_group in 
            (SELECT SGS.parent
				FROM `tabStudent Group Student` AS SGS
				INNER JOIN `tabStudent` AS Student
				ON SGS.student_name = Student.student_name
				WHERE Student.family_code = %s) 
            and docstatus<>2
			order by schedule_date asc limit {0} , {1}""".format(
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
        "title": _("Course Schedule"),
        "get_list": get_course_list,
        "row_template": "education/doctype/course_schedule/templates/course_schedule_row.html",
    }

