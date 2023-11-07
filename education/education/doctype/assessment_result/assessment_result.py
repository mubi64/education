# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.website.website_generator import WebsiteGenerator
from frappe.utils import flt
from frappe.utils.csvutils import getlink

import education.education
from education.education.api import get_assessment_details, get_grade


class AssessmentResult(WebsiteGenerator):
	def validate(self):
		if not self.route:
			self.route = "progress-report/" + self.name
		education.education.validate_student_belongs_to_group(
			self.student, self.student_group
		)
		self.validate_maximum_score()
		self.validate_grade()
		self.validate_duplicate()

	def validate_maximum_score(self):
		assessment_details = get_assessment_details(self.assessment_plan)
		max_scores = {}
		for d in assessment_details:
			max_scores.update({d.assessment_criteria: d.maximum_score})

		for d in self.details:
			d.maximum_score = max_scores.get(d.assessment_criteria)
			if d.score > d.maximum_score:
				frappe.throw(_("Score cannot be greater than Maximum Score"))

	def validate_grade(self):
		self.total_score = 0.0
		for d in self.details:
			d.grade = get_grade(self.grading_scale, (flt(d.score) / d.maximum_score) * 100)
			self.total_score += d.score
		self.grade = get_grade(
			self.grading_scale, (self.total_score / self.maximum_score) * 100
		)

	def validate_duplicate(self):
		assessment_result = frappe.get_list(
			"Assessment Result",
			filters={
				"name": ("not in", [self.name]),
				"student": self.student,
				"assessment_plan": self.assessment_plan,
				"docstatus": ("!=", 2),
			},
		)
		if assessment_result:
			frappe.throw(
				_("Assessment Result record {0} already exists.").format(
					getlink("Assessment Result", assessment_result[0].name)
				)
			)


def get_assessment_result_list(
        doctype, txt, filters, limit_start, limit_page_length=20, order_by="modified"
):
    user = frappe.session.user
    guardian = frappe.db.sql(
        "select family_code from `tabGuardian` where user= %s limit 1", user
    )
    if guardian:
        return frappe.db.sql(
            """
			select name, assessment_plan, program, course, grading_scale, assessment_group, student_group, route
			from `tabAssessment Result`
			where student in 
            (select name from `tabStudent` where family_code=%s) 
            and docstatus<>2
			order by name asc limit {0} , {1}""".format(
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
        "title": _("Progress Report"),
        "get_list": get_assessment_result_list,
        "row_template": "education/doctype/assessment_result/templates/assessment_result_row.html",
    }