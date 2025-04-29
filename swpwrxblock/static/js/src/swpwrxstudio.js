/* Javascript for SWREACTXStudio. */
function SWREACTXStudio(runtime, element, question) {
  // Stub notify so xblock doesn't crash in dev
  if (typeof runtime.notify === "undefined") {
    runtime.notify = function () {
      console.info(arguments);
    };
  }

  var handlerUrl = runtime.handlerUrl(element, "save_question");

  $(".save-button", element).click(function (eventObject) {
    var data = {
      q_weight: $("#q_weight", element).val(),
      q_max_attempts: $("#q_max_attempts", element).val(),
      q_option_showme: $("#q_option_showme", element).val(),
      q_option_hint: $("#q_option_hint", element).val(),
      q_grade_showme_ded: $("#q_grade_showme_ded", element).val(),
      q_grade_hints_count: $("#q_grade_hints_count", element).val(),
      q_grade_hints_ded: $("#q_grade_hints_ded", element).val(),
      q_grade_errors_count: $("#q_grade_errors_count", element).val(),
      q_grade_errors_ded: $("#q_grade_errors_ded", element).val(),
      q_grade_min_steps_count: $("#q_grade_min_steps_count", element).val(),
      q_grade_min_steps_ded: $("#q_grade_min_steps_ded", element).val(),

      q_grade_app_key: $("#q_grade_app_key", element).val(),
      id: $("#id", element).val(),
      label: $("#label", element).val(),
      stimulus: $("#stimulus", element).val(),
      definition: $("#definition", element).val(),
      qtype: $("#qtype", element).val(),
      display_math: $("#display_math", element).val(),
      hint1: $("#hint1", element).val(),
      hint2: $("#hint2", element).val(),
      hint3: $("#hint3", element).val(),
      swreact_problem: $("#swreact_problem", element).val(),
      swreact_rank: $("#swreact_rank", element).val(),
      swreact_invalid_schemas: $("#swreact_invalid_schemas", element).val(),
      swreact_problem_hints: $("#swreact_problem_hints", element).val(),
    };

    runtime.notify("save", { state: "start" });
    $.ajax({
      type: "POST",
      url: handlerUrl,
      data: JSON.stringify(data),
      success: null,
    }).done(function (response) {
      runtime.notify("save", { state: "end" });
    });
  });

  $(".cancel-button", element).click(function (eventObject) {
    runtime.notify("cancel", {});
  });

  /* PAGE LOAD EVENT */
  $(function ($) {});
}
