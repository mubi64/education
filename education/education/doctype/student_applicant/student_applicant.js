// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Student Applicant", {
  setup: function (frm) {
    frm.add_fetch("guardian", "guardian_name", "guardian_name");
  },

  refresh: function (frm) {
    frm.set_query("academic_term", function (doc, cdt, cdn) {
      return {
        filters: {
          academic_year: frm.doc.academic_year,
        },
      };
    });

    if (!frm.is_new() && frm.doc.paid === 1) {
      frm.add_custom_button(
        __("Accounting Ledger"),
        function () {
          frappe.route_options = {
            voucher_no: frm.doc.name,
            from_date: frm.doc.posting_date,
            to_date: moment(frm.doc.modified).format("YYYY-MM-DD"),
            company: frm.doc.company,
            group_by: "",
            show_cancelled_entries: frm.doc.docstatus === 2,
          };
          frappe.set_route("query-report", "General Ledger");
        },
        __("View")
      );
    }

    if (frm.is_new()) {
      frm.set_value("paid", 0);
    }

    if (!frm.is_new() && frm.doc.application_status === "Applied") {
      frm.add_custom_button(
        __("Approve"),
        function () {
          frm.set_value("application_status", "Approved");
          frm.save_or_update();
        },
        __("Actions")
      );

      frm.add_custom_button(
        __("Reject"),
        function () {
          frm.set_value("application_status", "Rejected");
          frm.save_or_update();
        },
        __("Actions")
      );
      if (frm.doc.paid !== 1) {
        frm.add_custom_button(
          __("Make Payment"),
          function () {
            console.log("Make Payment");
            frappe.call({
              method:
                "education.education.doctype.student_applicant.student_applicant.make_payment",
              args: {
                doc: frm.doc,
                current_docname: frm.doc.name,
              },
              callback: function (r) {
                frm.set_value("paid", 1);
                frm.save_or_update();
                console.log(r.message, "Response Make Payment");
                // frm.reload_doc();
              },
            });
          },
          __("Actions")
        );
      }
    }

    if (!frm.is_new() && frm.doc.application_status === "Approved") {
      frm
        .add_custom_button(__("Enroll"), function () {
          frm.events.enroll(frm);
        })
        .addClass("btn-primary");

      frm.add_custom_button(
        __("Reject"),
        function () {
          frm.set_value("application_status", "Rejected");
          frm.save_or_update();
        },
        "Actions"
      );
    }

    frappe.realtime.on("enroll_student_progress", function (data) {
      if (data.progress) {
        frappe.hide_msgprint(true);
        frappe.show_progress(
          __("Enrolling student"),
          data.progress[0],
          data.progress[1]
        );
      }
    });

    frappe.db.get_value(
      "Education Settings",
      { name: "Education Settings" },
      "user_creation_skip",
      (r) => {
        if (r.account_paid_to && !frm.doc.account_paid_to) {
          frm.set_value("account_paid_to", r.account_paid_to);
        }
        if (r.income_account && !frm.doc.income_account) {
          frm.set_value("income_account", r.income_account);
        }
        if (cint(r.user_creation_skip) !== 1) {
          frm.set_df_property("student_email_id", "reqd", 1);
        }
      }
    );
  },

  enroll: function (frm) {
    frappe.model.open_mapped_doc({
      method: "education.education.api.enroll_student",
      frm: frm,
    });
  },
  student_admission: function (frm) {
    if (frm.doc.student_admission) {
      frappe.call({
        method: "education.education.api.get_student_admission",
        args: {
          name: frm.doc.student_admission,
        },
        callback: function (r) {
          var res = r.message;
          if (res) {
            var total = 0;
            if (frm.doc.program) {
              if (res.program_details.length > 0) {
                for (let e = 0; e < res.program_details.length; e++) {
                  if (frm.doc.program == res.program_details[e].program) {
                    total = res.program_details[e].application_fee;
                  }
                }
              }
            } else {
              frappe.msgprint(__("Please select program"));
            }
            frm.set_value("total", total);
            frm.set_value("taxes_and_charges", "");
          }
        },
      });
    }
  },
  taxes_and_charges: function (frm) {
    if (frm.doc.taxes_and_charges) {
      frm.set_value("taxes", "");
      frm.set_value("total_taxes_and_charges", "");
      frm.set_value("total_taxes_and_charges_company_currency", "");
      // frm.set_value("grand_total_before_tax", frm.doc.total);
      // frm.set_value("grand_total", frm.doc.total);
      frappe.call({
        method: "education.education.api.get_fee_sales_charges",
        args: {
          taxes_and_charges: frm.doc.taxes_and_charges,
        },
        callback: function (r) {
          if (r.message) {
            $.each(r.message, function (i, d) {
              var row = frappe.model.add_child(
                frm.doc,
                "Sales Taxes and Charges",
                "taxes"
              );
              row.charge_type = d.charge_type;
              row.account_head = d.account_head;
              row.included_in_print_rate = d.included_in_print_rate;
              row.rate = d.rate;
              row.cost_center = d.cost_center;
              row.description = d.description;
            });
          }
          if (frm.doc.student_admission) {
            frappe.call({
              method: "education.education.api.get_student_admission",
              args: {
                name: frm.doc.student_admission,
              },
              callback: function (r) {
                var tax_and_charges = 0;
                var res = r.message;
                if (res) {
                  var taxes = frm.doc.taxes;
                  for (let i = 0; i < taxes.length; i++) {
                    var rate_persent = taxes[i].rate / 100;
                    var total_amount = 0;
                    var amount = 0;

                    if (res.program_details.length > 0) {
                      for (let e = 0; e < res.program_details.length; e++) {
                        if (frm.doc.program == res.program_details[e].program) {
                          total_amount = res.program_details[e].application_fee;
                          amount =
                            rate_persent *
                            res.program_details[e].application_fee;
                        }
                      }
                    }
                    if (taxes[i].included_in_print_rate == 1) {
                      let rate_plus_1 = rate_persent + 1;
                      total_amount = total_amount + amount;
                      let total = total_amount / rate_plus_1;
                      taxes[i].tax_amount = total_amount - total;
                      taxes[i].total = total;
                      tax_and_charges += total_amount - total;
                      // frm.set_value(
                      //   "grand_total",
                      //   frm.doc.grand_total - (total_amount - total)
                      // );
                      // frm.set_value(
                      //   "grand_total_before_tax",
                      //   frm.doc.grand_total_before_tax - (total_amount - total)
                      // );
                    } else {
                      taxes[i].tax_amount = amount;
                      taxes[i].total = total_amount + amount;
                      tax_and_charges += amount;
                    }
                  }
                  frm.set_value("total_taxes_and_charges", tax_and_charges);
                  frm.set_value(
                    "total_taxes_and_charges_company_currency",
                    tax_and_charges
                  );
                  // frm.set_value("grand_total_before_tax", total - tax_and_charges);
                  // frm.set_value(
                  //   "grand_total",
                  //   frm.doc.grand_total + tax_and_charges
                  // );
                  // frm.set_value(
                  //   "grand_total",
                  //   grand_total_before_tax + tax_and_charges
                  // );
                }
                refresh_field("taxes");
              },
            });
          } else {
            frappe.msgprint(__("Please select student admission"));
          }
        },
      });
    }
  },
});

frappe.ui.form.on("Sales Taxes and Charges", {
  included_in_print_rate: function (frm, cdt, cdn) {
    var tax = frappe.get_doc(cdt, cdn);
    if (tax) {
      var total_amount = 0;
      var amount = 0;
      var rate = tax.rate / 100;
      if (tax.included_in_print_rate == 1) {
        total_amount = tax.total;
        let rate_plus_1 = rate + 1;
        let total = total_amount / rate_plus_1;
        amount = total_amount - total;
        tax.tax_amount = amount;
        tax.total = total;
        // frm.set_value("grand_total", frm.doc.grand_total - amount);
        // frm.set_value(
        //   "grand_total_before_tax",
        //   frm.doc.grand_total_before_tax - amount
        // );
      } else {
        frappe.call({
          method: "education.education.api.get_student_admission",
          args: {
            name: frm.doc.student_admission,
          },
          callback: function (r) {
            var res = r.message;
            if (res) {
              if (res.program_details) {
                for (let e = 0; e < res.program_details.length; e++) {
                  if (frm.doc.program == res.program_details[e].program) {
                    total_amount = res.program_details[e].application_fee;
                    amount = rate * res.program_details[e].application_fee; // comp_amount;
                  }
                }
              }
              tax.tax_amount = amount;
              tax.total = total_amount + amount;
              // frm.set_value("grand_total", frm.doc.grand_total + amount);
              // frm.set_value(
              //   "grand_total_before_tax",
              //   frm.doc.grand_total_before_tax + amount
              // );
            }
          },
        });
      }
      frm.fields_dict.taxes.grid.refresh();
    }
  },
});

frappe.ui.form.on("Student Sibling", {
  setup: function (frm) {
    frm.add_fetch("student", "title", "full_name");
    frm.add_fetch("student", "gender", "gender");
    frm.add_fetch("student", "date_of_birth", "date_of_birth");
  },
});
