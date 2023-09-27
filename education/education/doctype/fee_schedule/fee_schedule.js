// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
frappe.provide("erpnext.accounts.dimensions");
frappe.ui.form.on("Fee Schedule", {
  setup: function (frm) {
    frm.add_fetch("fee_structure", "receivable_account", "receivable_account");
    frm.add_fetch("fee_structure", "income_account", "income_account");
    frm.add_fetch("fee_structure", "cost_center", "cost_center");
  },

  company: function (frm) {
    erpnext.accounts.dimensions.update_dimension(frm, frm.doctype);
  },

  onload: function (frm) {
    frm.set_query("receivable_account", function (doc) {
      return {
        filters: {
          account_type: "Receivable",
          is_group: 0,
          company: doc.company,
        },
      };
    });

    frm.set_query("income_account", function (doc) {
      return {
        filters: {
          account_type: "Income Account",
          is_group: 0,
          company: doc.company,
        },
      };
    });

    frm.set_query("student_group", "student_groups", function () {
      return {
        program: frm.doc.program,
        academic_term: frm.doc.academic_term,
        academic_year: frm.doc.academic_year,
        disabled: 0,
      };
    });

    frappe.realtime.on("fee_schedule_progress", function (data) {
      if (data.reload && data.reload === 1) {
        frm.reload_doc();
      }
      if (data.progress) {
        let progress_bar = $(cur_frm.dashboard.progress_area.body).find(
          ".progress-bar"
        );
        if (progress_bar) {
          $(progress_bar)
            .removeClass("progress-bar-danger")
            .addClass("progress-bar-success progress-bar-striped");
          $(progress_bar).css("width", data.progress + "%");
        }
      }
    });

    erpnext.accounts.dimensions.setup_dimension_filters(frm, frm.doctype);
  },

  refresh: function (frm) {
    // frm.trigger("taxes_and_charges");
    if (
      !frm.doc.__islocal &&
      frm.doc.__onload &&
      frm.doc.__onload.dashboard_info &&
      frm.doc.fee_creation_status === "Successful"
    ) {
      var info = frm.doc.__onload.dashboard_info;
      frm.dashboard.add_indicator(
        __("Total Collected: {0}", [
          format_currency(info.total_paid, info.currency),
        ]),
        "blue"
      );
      frm.dashboard.add_indicator(
        __("Total Outstanding: {0}", [
          format_currency(info.total_unpaid, info.currency),
        ]),
        info.total_unpaid ? "orange" : "green"
      );
    }
    if (frm.doc.fee_creation_status === "In Process") {
      frm.dashboard.add_progress("Fee Creation Status", "0");
    }
    if (
      (frm.doc.docstatus === 1 && !frm.doc.fee_creation_status) ||
      frm.doc.fee_creation_status === "Failed"
    ) {
      frm
        .add_custom_button(__("Create Fees"), function () {
          frappe.call({
            method: "create_fees",
            doc: frm.doc,
            callback: function () {
              frm.refresh();
            },
          });
        })
        .addClass("btn-primary");
    }
    if (frm.doc.fee_creation_status === "Successful") {
      frm.add_custom_button(__("View Fees Records"), function () {
        frappe.route_options = {
          fee_schedule: frm.doc.name,
        };
        frappe.set_route("List", "Fees");
      });
    }
  },

  fee_structure: function (frm) {
    if (frm.doc.fee_structure) {
      frappe.call({
        method:
          "education.education.doctype.fee_schedule.fee_schedule.get_fee_structure",
        args: {
          target_doc: frm.doc.name,
          source_name: frm.doc.fee_structure,
        },
        callback: function (r) {
          var doc = frappe.model.sync(r.message);
          frappe.set_route("Form", doc[0].doctype, doc[0].name);
        },
      });
    }
  },

  get_student_groups: function (frm) {
    frm.set_value("student_groups", "");
    if (frm.doc.program) {
      frappe.db
        .get_list("Student Group", {
          fields: ["*"],
          filters: [["program", "like", frm.doc.program]], //[["name", "like", frm.doc.program]]
          order_by: "name",
        })
        .then((rec) => {
          //   console.log(rec, frm.doc.program, "check values ");
          for (let i = 0; i < rec.length; i++) {
            const ele = rec[i];
            frappe.call({
              method:
                "education.education.doctype.fee_schedule.fee_schedule.get_total_students",
              args: {
                student_group: ele.name,
                academic_year: frm.doc.academic_year,
                academic_term: frm.doc.academic_term,
                student_category: frm.doc.student_category,
              },
              callback: function (r) {
                if (!r.exc) {
                  frm.add_child("student_groups", {
                    student_group: ele.name,
                    total_students: r.message,
                  });
                  // Sort the array by the "name" property
                  frm.doc.student_groups.sort((a, b) => {
                    const nameA = a.student_group.toUpperCase(); // Convert names to uppercase for case-insensitive sorting
                    const nameB = b.student_group.toUpperCase();

                    if (nameA < nameB) {
                      return -1;
                    }

                    if (nameA > nameB) {
                      return 1;
                    }

                    return 0; // Names are equal
                  });
                  refresh_field("student_groups");
                }
              },
            });
          }
          if (frm.doc.taxes != null || frm.doc.taxes_and_charges != null) {
            frm.trigger("taxes_and_charges");
          }
        });
    }
  },

  taxes_and_charges: function (frm) {
    frm.set_value("taxes", "");
    frm.set_value("total_taxes_and_charges", 0);
    if (frm.doc.taxes_and_charges) {
      frappe.call({
        method: "education.education.api.get_fee_sales_charges",
        args: {
          taxes_and_charges: frm.doc.taxes_and_charges,
        },
        callback: function (r) {
          var amount;
          if (r.message) {
            $.each(r.message, function (i, d) {
              var row = frappe.model.add_child(
                frm.doc,
                "Sales Taxes and Charges",
                "taxes"
              );
              var rate_persent = d.rate / 100;
              amount = rate_persent * frm.doc.total_amount;
              row.charge_type = d.charge_type;
              row.account_head = d.account_head;
              row.rate = d.rate;
              row.total = amount + frm.doc.total_amount;
              row.base_total = d.base_total;
              row.cost_center = d.cost_center;
              row.description = d.description;
              row.tax_amount = amount;
              for (let i = 0; i < frm.doc.student_groups.length; i++) {
                frm.doc.total_taxes_and_charges +=
                  amount * frm.doc.student_groups[i].total_students;
              }
            });
          }
          refresh_field("taxes");
          refresh_field("total_taxes_and_charges");
          // frm.doc.grand_total_before_tax = frm.doc.grand_total
          // refresh_field("grand_total_before_tax");
          frm.set_value(
            "total_taxes_and_charges_company_currency",
            frm.doc.total_taxes_and_charges
          );
        },
      });
    }
  },
});

frappe.ui.form.on("Fee Schedule Student Group", {
  student_group: function (frm, cdt, cdn) {
    var row = locals[cdt][cdn];
    if (row.student_group && frm.doc.academic_year) {
      frappe.call({
        method:
          "education.education.doctype.fee_schedule.fee_schedule.get_total_students",
        args: {
          student_group: row.student_group,
          academic_year: frm.doc.academic_year,
          academic_term: frm.doc.academic_term,
          student_category: frm.doc.student_category,
        },
        callback: function (r) {
          if (!r.exc) {
            frappe.model.set_value(cdt, cdn, "total_students", r.message);
          }
        },
      });
    }
  },
});
