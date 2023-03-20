// Copyright (c) 2016, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on("Program Enrollment", {
  setup: function (frm) {
    frm.add_fetch("fee_structure", "total_amount", "amount");
  },

  onload: function (frm) {
    frm.set_query("academic_term", function () {
      return {
        filters: {
          academic_year: frm.doc.academic_year,
        },
      };
    });

    frm.set_query("academic_term", "fees", function () {
      return {
        filters: {
          academic_year: frm.doc.academic_year,
        },
      };
    });

    frm.fields_dict["fees"].grid.get_field("fee_structure").get_query =
      function (doc, cdt, cdn) {
        var d = locals[cdt][cdn];
        return {
          filters: { academic_term: d.academic_term },
        };
      };

    if (frm.doc.program) {
      frm.set_query("course", "courses", function () {
        return {
          query:
            "education.education.doctype.program_enrollment.program_enrollment.get_program_courses",
          filters: {
            program: frm.doc.program,
          },
        };
      });
    }

    frm.set_query("student", function () {
      return {
        query:
          "education.education.doctype.program_enrollment.program_enrollment.get_students",
        filters: {
          academic_year: frm.doc.academic_year,
          academic_term: frm.doc.academic_term,
        },
      };
    });
  },

  program: function (frm) {
    frm.events.get_courses(frm);
    if (frm.doc.program) {
      frappe.call({
        method: "education.education.api.get_fee_schedule",
        args: {
          program: frm.doc.program,
          student_category: frm.doc.student_category,
        },
        callback: function (r) {
          if (r.message) {
            frm.set_value("fees", r.message);
            frm.events.get_courses(frm);
          }
        },
      });
    }
  },

  student_category: function () {
    frappe.ui.form.trigger("Program Enrollment", "program");
  },

  get_courses: function (frm) {
    frm.program_courses = [];
    frm.set_value("courses", []);
    frappe.call({
      method: "get_courses",
      doc: frm.doc,
      callback: function (r) {
        if (r.message) {
          frm.program_courses = r.message;
          frm.set_value("courses", r.message);
        }
      },
    });
  },
  taxes_and_charges: function (frm) {
    frm.set_value("taxes", "");
    if (frm.doc.taxes_and_charges) {
      frappe.call({
        method: "education.education.api.get_fee_sales_charges",
        args: {
          taxes_and_charges: frm.doc.taxes_and_charges,
        },
        callback: function (r) {
          var amount;
          var comp_amount = 0;
          for (let i = 0; i < frm.doc.fees.length; i++) {
            comp_amount += frm.doc.fees[i].amount;
          }
          if (r.message) {
            $.each(r.message, function (i, d) {
              var row = frappe.model.add_child(
                frm.doc,
                "Sales Taxes and Charges",
                "taxes"
              );
              var rate_persent = d.rate / 100;
              amount = rate_persent * comp_amount;
              row.charge_type = d.charge_type;
              row.account_head = d.account_head;
              row.rate = d.rate;
              row.total = amount + comp_amount;
              row.base_total = d.base_total;
              row.cost_center = d.cost_center;
              row.description = d.description;
              row.tax_amount = amount;
            });
          }
          refresh_field("taxes");
        },
      });
    }
  },
});

frappe.ui.form.on("Sales Taxes and Charges", {
  included_in_print_rate: function (frm) {
    if (frm.doc.taxes) {
      var taxes = frm.doc.taxes;
      for (let i = 0; i < taxes.length; i++) {
        if (taxes[i].included_in_print_rate == 1) {
          let rate = taxes[i].rate / 100;
          let total_amount = taxes[i].total;
          let rate_plus_1 = rate + 1;
          let total = total_amount / rate_plus_1;
          taxes[i].tax_amount = total_amount - total;
          taxes[i].total = total;
        } else {
          if (frm.doc.taxes_and_charges) {
            frappe.call({
              method: "education.education.api.get_fee_sales_charges",
              args: {
                taxes_and_charges: frm.doc.taxes_and_charges,
              },
              callback: function (r) {
                var amount;
                var comp_amount = 0;
                for (let i = 0; i < frm.doc.fees.length; i++) {
                  comp_amount += frm.doc.fees[i].amount;
                }
                if (r.message) {
                  $.each(r.message, function (i, d) {
                    var rate_persent = d.rate / 100;
                    amount = rate_persent * comp_amount;
                    taxes[i].total = amount + comp_amount;
                    taxes[i].tax_amount = amount;
                  });
                }
              },
            });
          }
        }
      }
      frm.fields_dict.taxes.grid.refresh();
    }
  },
});

frappe.ui.form.on("Program Enrollment Course", {
  courses_add: function (frm) {
    frm.fields_dict["courses"].grid.get_field("course").get_query = function (
      doc
    ) {
      var course_list = [];
      if (!doc.__islocal) course_list.push(doc.name);
      $.each(doc.courses, function (_idx, val) {
        if (val.course) course_list.push(val.course);
      });
      return {
        filters: [
          ["Course", "name", "not in", course_list],
          ["Course", "name", "in", frm.program_courses.map((e) => e.course)],
        ],
      };
    };
  },
});
