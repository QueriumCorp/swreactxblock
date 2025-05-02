/* Javascript for SWREACTXBlock.
 * TODO:  Enforce assignment due date for not starting another attempt.
 *        Disable Hint and ShowMe buttons if options are set.
 */

var handlerUrlSwreactFinalResults; // Define this globally where it can be found by the React swreact onComplete code
var handlerUrlSwreactPartialResults; // Define this globally where it can be found by the React swreact onStep code

function SWREACTXStudent(runtime, element) {
  console.info("SWREACTXStudent start");
  console.info("SWREACTXStudent element", element);

  var handlerUrlGetData = runtime.handlerUrl(element, "get_data");

  handlerUrlSwreactFinalResults = runtime.handlerUrl(
    element,
    "save_swreact_final_results",
  ); // Leave a handlerUrl for the SWREACT onSubmit callback
  handlerUrlSwreactPartialResults = runtime.handlerUrl(
    element,
    "save_swreact_partial_results",
  ); // Leave a handlerUrl for the SWREACT onSubmit callback

  console.info("SWREACTXStudent calling get_data at ", handlerUrlGetData);

  // Now we do the question manipulation in swreactxblock.py
  // const SWPHASE = 5;          // Which element of the POWER steps array in window.swreact_problem contains the StepWise UI?

  $(".SWReactComponent").show(); // Show React app root div

  $(".sequence-bottom").hide(); // Don't show the EdX sequential navigation buttons that lie on top of the react div
  $(".unit-navigation").hide(); // Don't show the EdX sequential navigation buttons that lie on top of the react div
  $(".problem-complete").hide(); // Don't show the 'problem is complete' message
  $(".wrap-instructor-info").hide(); // Don't show the 'staff debug' button

  get_data_data = {}; // don't need to sent any data to get_data

  $.ajax({
    type: "POST",
    url: handlerUrlGetData,
    data: JSON.stringify(get_data_data),
    error: function (XMLHttpRequest, textStatus, errorThrown) {
      console.info(
        "SWREACTXstudent get_data POST error textStatus=",
        textStatus,
        " errorThrown=",
        errorThrown,
      );
      // alert("Status: " + textStatus); alert("Error: " + errorThrown);
    },
    success: function (data, msg) {
      console.info("SWREACTXstudent GET success");
      console.info("SWREACTXstudent GET data", data);
      console.info("SWREACTXstudent GET msg", msg);

      var data_obj = JSON.parse(data);
      console.info("SWREACTXstudent GET data_obj", data_obj);

      // Set our context variables from the data we receive
      var question = data_obj.question;
      var grade = data_obj.grade;
      // We no longer pass in solution.
      // var solution = data_obj.solution;
      var count_attempts = data_obj.count_attempts;
      var variants_count = data_obj.variants_count;
      var max_attempts = data_obj.max_attempts;
      // var enable_showme = question.q_option_showme;
      // var enable_hint = question.q_option_hint;
      var weight = question.q_weight;
      var min_steps = question.q_grade_min_steps_count;
      var min_steps_ded = question.q_grade_min_steps_ded;
      var swreact_id = question.q_id;

      console.info("SWREACTXStudent question ID", swreact_id);
      console.info("SWREACTXStudent question", question);
      console.info("SWREACTXStudent count_attempts", count_attempts);
      console.info("SWREACTXStudent variants_counnt", variants_count);
      console.info("SWREACTXStudent max_attempts", max_attempts);
      console.info("SWREACTXStudent weight ", weight);
      console.info("SWREACTXStudent min steps", min_steps);
      console.info("SWREACTXStudent min steps dec", min_steps_ded);
      console.info("SWREACTXStudent grade", grade);

      /* PAGE LOAD EVENT */
      $(function ($) {});
    }, // end of success block
  });
  console.info("SWREACTXStudent end");
}
