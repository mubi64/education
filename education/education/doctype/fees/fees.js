// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.accounts.dimensions");
var checked_id = {};

frappe.ui.form.on("Fees", {
  setup: function (frm) {
    frm.add_fetch("fee_structure", "receivable_account", "receivable_account");
    frm.add_fetch("fee_structure", "income_account", "income_account");
    frm.add_fetch("fee_structure", "cost_center", "cost_center");
  },

  company: function (frm) {
    erpnext.accounts.dimensions.update_dimension(frm, frm.doctype);
  },

  onload: function (frm) {
    frm.set_query("academic_term", function () {
      return {
        filters: {
          academic_year: frm.doc.academic_year,
        },
      };
    });
    frm.set_query("fee_structure", function () {
      return {
        filters: {
          academic_year: frm.doc.academic_year,
        },
      };
    });
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
    if (!frm.doc.posting_date) {
      frm.doc.posting_date = frappe.datetime.get_today();
    }

    erpnext.accounts.dimensions.setup_dimension_filters(frm, frm.doctype);
  },

  // validate: function (frm) {
  // 	if (frm.doc.outstanding_amount == 0) {
  // 		var isRecorded = true
  // 		for (let i = 0; i < frm.doc.components.length; i++) {
  // 			if (frm.doc.components[i].income_recorded === 0) {
  // 				isRecorded = false
  // 				break
  // 			}
  // 		}
  // 		if (!isRecorded) {
  // 			frm.page.set_indicator(__("Paid, Income not Recorded"), "orange")
  // 			// frm.set_value("doc_status", "Paid, Income not Recorded");
  // 		}
  // 	}
  // },

  befor_save: async function (frm) {
    // var com = await
    // console.log(com, "Sdflsdkgsh");
    if (frm.doc.taxes_and_charges) {
      await frm.trigger("taxes_and_charges");
    }
  },

  refresh: function (frm) {
    var name = frm.doc.name;
    if (frm.doc.docstatus == 0) {
      frm.doc.components.filter((e) => {
        if (e.income_recorded == 1) {
          e.income_recorded = 0;
          return e;
        }
      });
      refresh_field("components");
    }
    // setTimeout(() => {
    //   frm.page.remove_inner_button("Duplicate", "Menu");
    // }, 1000);
    // if (frm.doc.docstatus == 1) {
    // 	if (frm.doc.outstanding_amount > 0) {
    // 		frm.page.set_indicator(__("Unpaid"), "orange")
    // 	} else {
    // 		var isRecorded = true
    // 		for (let i = 0; i < frm.doc.components.length; i++) {
    // 			if (frm.doc.components[i].income_recorded === 0) {
    // 				isRecorded = false
    // 				break
    // 			}
    // 		}
    // 		if (!isRecorded) {
    // 			frm.page.set_indicator(__("Paid, Income not Recorded"), "orange")
    // 			// frm.doc.doc_status = "Paid, Income not Recorded"
    // 		}
    // 	}
    // }
    if (frm.doc.docstatus == 0 && frm.doc.set_posting_time) {
      frm.set_df_property("posting_date", "read_only", 0);
      frm.set_df_property("posting_time", "read_only", 0);
    } else {
      frm.set_df_property("posting_date", "read_only", 1);
      frm.set_df_property("posting_time", "read_only", 1);
    }
    if (frm.doc.docstatus > 0) {
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
      frm.add_custom_button(
        __("Payments"),
        function () {
          frappe.set_route("List", "Payment Entry", {
            "Payment Entry Reference.reference_name": frm.doc.name,
          });
        },
        __("View")
      );
    }
    if (frm.doc.docstatus === 1 && frm.doc.outstanding_amount > 0) {
      frm.add_custom_button(
        __("Payment Request"),
        function () {
          frm.events.make_payment_request(frm);
        },
        __("Create")
      );
      frm.page.set_inner_btn_group_as_primary(__("Create"));
    }
    var comp = frm.doc.components.filter((e) => {
      if (e.income_recorded !== 1) return e;
    });
    if (frm.doc.docstatus === 1 && frm.doc.outstanding_amount != 0) {
      frm.add_custom_button(
        __("Payment"),
        function () {
          let d = new frappe.ui.Dialog({
            title: __("Payment"),
            fields: [
              {
                label: "Components",
                fieldname: "components",
                fieldtype: "Table",
                cannot_add_rows: true,
                cannot_delete_rows: true,
                read_only: 1,
                in_place_edit: true,
                data: frm.doc.components.filter((e) => {
                  if (checked_id[name]) {
                    checked_id[name].map((id) => {
                      if (e.idx === id) {
                        e.__checked = 1;
                      }
                    });
                  }
                  return e;
                }),
                fields: [
                  {
                    fieldname: "fees_category",
                    fieldtype: "Link",
                    in_list_view: 1,
                    label: "Fees Category",
                  },
                  {
                    fieldname: "amount",
                    fieldtype: "Currency",
                    in_list_view: 1,
                    label: "Amount",
                  },
                  {
                    fieldname: "amount_after_tax",
                    fieldtype: "Currency",
                    in_list_view: 1,
                    label: "Amount After Tax",
                  },
                ],
              },
            ],
            primary_action_label: "Payment",
            primary_action(fees) {
              let selectedFee = fees.components.filter((comp) => {
                if (comp.__checked === 1) {
                  return comp;
                }
              });
              var amount = 0;
              for (let i = 0; i < selectedFee.length; i++) {
                if (selectedFee[i].amount_after_tax) {
                  amount += selectedFee[i].amount_after_tax;
                } else {
                  amount += selectedFee[i].amount;
                }
              }
              if (selectedFee.length > 0) {
                if (amount <= frm.doc.outstanding_amount) {
                  frm.events.make_payment_entry(frm, amount);
                  d.hide();
                } else {
                  frappe.show_alert(
                    {
                      message: __(
                        "Amount should not be greater than outstanding amount"
                      ),
                      indicator: "red",
                    },
                    5
                  );
                }
              } else {
                frappe.show_alert(
                  {
                    message: __("Pleace select the components"),
                    indicator: "red",
                  },
                  5
                );
              }
            },
          });

          d.show();
        },
        __("Create")
      );
      frm.page.set_inner_btn_group_as_primary(__("Create"));
    }
    if (
      frm.doc.docstatus === 1 &&
      frm.doc.record_income_in_temp_account &&
      comp.length > 0
    ) {
      frm.add_custom_button(
        __("Record Income"),
        function () {
          let d = new frappe.ui.Dialog({
            title: __("Record Income"),
            fields: [
              {
                label: "Components",
                fieldname: "components",
                fieldtype: "Table",
                cannot_add_rows: true,
                cannot_delete_rows: true,
                read_only: 1,
                in_place_edit: true,
                data: frm.doc.components.filter((e) => {
                  if (e.income_recorded !== 1) return e;
                }),
                fields: [
                  {
                    fieldname: "fees_category",
                    fieldtype: "Link",
                    in_list_view: 1,
                    label: "Fees Category",
                  },
                  {
                    fieldname: "amount",
                    fieldtype: "Currency",
                    in_list_view: 1,
                    label: "Amount",
                  },
                  {
                    fieldname: "amount_after_tax",
                    fieldtype: "Currency",
                    in_list_view: 1,
                    label: "Amount After Tax",
                  },
                ],
              },
            ],
            primary_action_label: "Update",
            primary_action(fees) {
              checked_id[name] = [];
              let selectedFee = fees.components.filter((comp) => {
                if (comp.__checked === 1) {
                  checked_id[name].push(comp.idx);
                  return comp;
                }
              });
              if (selectedFee.length > 0) {
                frappe.call({
                  method: "education.education.doctype.fees.fees.record_income",
                  args: {
                    fees: selectedFee,
                    current_docname: frm.doc.name,
                  },
                  callback: function (r) {
                    frm.reload_doc();
                  },
                });
                d.hide();
                frappe.show_alert(
                  {
                    message: __("Document updated"),
                    indicator: "green",
                  },
                  5
                );
              } else {
                frappe.show_alert(
                  {
                    message: __("Pleace select the components"),
                    indicator: "red",
                  },
                  5
                );
              }
            },
          });

          d.show();
        },
        __("Create")
      );
      frm.page.set_inner_btn_group_as_primary(__("Create"));
    }
  },

  student: function (frm) {
    if (frm.doc.student) {
      checked_id = {};
      frappe.call({
        method: "education.education.api.get_current_enrollment",
        args: {
          student: frm.doc.student,
          academic_year: frm.doc.academic_year,
        },
        callback: function (r) {
          if (r) {
            $.each(r.message, function (i, d) {
              frm.set_value(i, d);
            });
          }
        },
      });
    }
  },

  make_payment_request: function (frm) {
    if (!frm.doc.student_email) {
      frappe.msgprint(
        __(
          "Please set the Email ID for the Student to send the Payment Request"
        )
      );
    } else {
      frappe.call({
        method:
          "erpnext.accounts.doctype.payment_request.payment_request.make_payment_request",
        args: {
          dt: frm.doc.doctype,
          dn: frm.doc.name,
          party_type: "Student",
          party: frm.doc.student,
          recipient_id: frm.doc.student_email,
        },
        callback: function (r) {
          if (!r.exc) {
            var doc = frappe.model.sync(r.message);
            frappe.set_route("Form", doc[0].doctype, doc[0].name);
          }
        },
      });
    }
  },

  make_payment_entry: function (frm, amount) {
    return frappe.call({
      method:
        "erpnext.accounts.doctype.payment_entry.payment_entry.get_payment_entry",
      args: {
        dt: frm.doc.doctype,
        dn: frm.doc.name,
        party_type: "Student",
        payment_type: "Receive",
      },
      callback: function (r) {
        r.message.paid_amount = amount;
        r.message.references[0].allocated_amount = amount;
        r.message.total_allocated_amount = amount;
        var doc = frappe.model.sync(r.message);
        frappe.set_route("Form", doc[0].doctype, doc[0].name);
      },
    });
  },

  set_posting_time: function (frm) {
    frm.refresh();
  },

  academic_term: function () {
    frappe.ui.form.trigger("Fees", "program");
  },

  fee_structure: function (frm) {
    if (!frm.doc.student) {
      frappe.msgprint(__("Please select the student"));
      return;
    }
    frm.set_value("components", "");
    if (frm.doc.fee_structure) {
      frappe.call({
        method: "education.education.api.get_fee_components",
        args: {
          fee_structure: frm.doc.fee_structure,
        },
        callback: function (r) {
          if (r.message) {
            $.each(r.message, function (i, d) {
              var row = frappe.model.add_child(
                frm.doc,
                "Fee Component",
                "components"
              );
              row.fees_category = d.fees_category;
              row.description = d.description;
              row.gross_amount = d.amount;
              row.amount = d.amount;
            });
          }
        },
      });
      frappe.call({
        method: "education.education.api.get_student_transportation",
        args: {
          student: frm.doc.student,
        },
        callback: function (r) {
          if (r.message) {
            var row = frappe.model.add_child(
              frm.doc,
              "Fee Component",
              "components"
            );
            row.fees_category = r.message.fee_category;
            row.gross_amount = r.message.fee_amount;
            row.amount = r.message.fee_amount;
          }
          refresh_field("components");
          frm.trigger("calculate_total_amount");
        },
      });
      frappe.call({
        method: "education.education.api.get_student_dicount",
        args: {
          student: frm.doc.student,
        },
        callback: function (r) {
          if (r.message) {
            var discounts = r.message.discount;
            var components = frm.doc.components;
            for (let e = 0; e < components.length; e++) {
              const component = components[e];
              for (let i = 0; i < discounts.length; i++) {
                const discount = discounts[i];
                if (component.fees_category == discount.fee_category) {
                  component.discount_type = discount.discount_type;
                  if (discount.discount_type == "Percentage") {
                    component.percentage = discount.percentage;
                    var percent = component.percentage / 100;
                    var discount_amount = percent * component.gross_amount;
                    component.amount = component.gross_amount - discount_amount;
                  } else if (discount.discount_type == "Amount") {
                    component.discount_amount = discount.amount;
                    component.amount =
                      component.gross_amount - component.discount_amount;
                  }
                }
              }
            }
            frm.fields_dict.components.grid.refresh();
            frm.trigger("taxes_and_charges");
          }
        },
      });
    }
  },

  taxes_and_charges: function (frm) {
    if (frm.doc.taxes_and_charges) {
      frm.set_value("taxes", "");
      frm.set_value("total_taxes_and_charges", 0);
      frm.set_value("total_taxes_and_charges_company_currency", 0);
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
              amount = rate_persent * frm.doc.grand_total_before_tax;
              row.charge_type = d.charge_type;
              row.account_head = d.account_head;
              row.rate = d.rate;
              row.included_in_print_rate = d.included_in_print_rate;
              row.total = amount + frm.doc.grand_total_before_tax;
              row.base_total = d.base_total;
              row.cost_center = d.cost_center;
              row.description = d.description;
              row.tax_amount = amount;
              frm.doc.total_taxes_and_charges += amount;
              frm.doc.total_taxes_and_charges_company_currency += amount;
            });
          }
          refresh_field("taxes");
          refresh_field("total_taxes_and_charges");
          refresh_field("total_taxes_and_charges_company_currency");
          frm.doc.grand_total =
            frm.doc.total_taxes_and_charges + frm.doc.grand_total_before_tax;
          refresh_field("grand_total");
        },
      });
    }
  },

  calculate_total_amount: function (frm) {
    var grand_total_before_tax = 0;
    for (var i = 0; i < frm.doc.components.length; i++) {
      grand_total_before_tax += frm.doc.components[i].amount;
    }
    frm.set_value("grand_total_before_tax", grand_total_before_tax);
    frm.trigger("taxes_and_charges");
  },
});

frappe.ui.form.on("Fee Component", {
  amount: function (frm) {
    frm.trigger("calculate_total_amount");
  },
  discount_type: function (frm) {
    var components = frm.doc.components;
    for (let i = 0; i < components.length; i++) {
      const component = components[i];
      if (component.discount_type == "Amount") {
        if (component.discount_amount) {
          component.amount = component.gross_amount - component.discount_amount;
          component.discount_type = "Amount";
        }
      } else if (component.discount_type == "Percentage") {
        if (component.percentage) {
          var percent = component.percentage / 100;
          var discount_amount = percent * component.gross_amount;
          component.amount = component.gross_amount - discount_amount;
          component.discount_type = "Percentage";
        }
      } else {
        component.amount = component.gross_amount;
      }
    }
    frm.trigger("calculate_total_amount");
    frm.fields_dict.components.grid.refresh();
  },
  percentage: function (frm) {
    var components = frm.doc.components;
    for (let i = 0; i < components.length; i++) {
      const component = components[i];
      if (component.percentage) {
        var percent = component.percentage / 100;
        var discount_amount = percent * component.gross_amount;
        component.amount = component.gross_amount - discount_amount;
        component.discount_type = "Percentage";
      }
    }
    frm.trigger("calculate_total_amount");
    frm.fields_dict.components.grid.refresh();
  },
  discount_amount: function (frm) {
    var components = frm.doc.components;
    for (let i = 0; i < components.length; i++) {
      const component = components[i];
      if (component.discount_amount) {
        component.amount = component.gross_amount - component.discount_amount;
        component.discount_type = "Amount";
      }
    }
    frm.trigger("calculate_total_amount");
    frm.fields_dict.components.grid.refresh();
  },
});
