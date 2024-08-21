/* Javascript for SWPWRXBlock.
 * TODO:  Enforce assignment due date for not starting another attempt.
 *        Disble Hint and ShowMe buttons if options are set.
 */

var handlerUrlSwpwrResults;  // Define this globally where it can be found by the React swpwr onSubmit code

function SWPWRXStudent(runtime, element) {

    console.info("SWPWRXStudent start");
    console.info("SWPWRXStudent element",element);

    var handlerUrlGetData = runtime.handlerUrl(element, 'get_data');

    handlerUrlSwpwrResults = runtime.handlerUrl(element, 'save_swpwr_results');   // Leave a handlerUrl for the SWPWR onSubmit callback

    console.info("SWPWRXStudent calling get_data at ",handlerUrlGetData);

    // Now we do the question manipulation in swpwrxblock.py
    // const SWPHASE = 5;          // Which element of the POWER steps array in window.swpwr_problem contains the StepWise UI?

    $('.SWPowerComponent').show();  // Show React app root div

    $('.sequence-bottom').hide();   // Don't show the EdX sequential navigation buttons that lie on top of the react div
    $('.unit-navigation').hide();   // Don't show the EdX sequential navigation buttons that lie on top of the react div
    $('.problem-complete').hide();  // Don't show the 'problem is complete' message

    get_data_data = {}		// don't need to sent any data to get_data

    $.ajax({
        type: "POST",
        url: handlerUrlGetData,
        data: JSON.stringify(get_data_data),
        error: function(XMLHttpRequest, textStatus, errorThrown) {
               console.info("SWPWRXstudent get_data POST error textStatus=",textStatus," errorThrown=",errorThrown);
               // alert("Status: " + textStatus); alert("Error: " + errorThrown);
        },
        success: function (data,msg) {
            console.info("SWPWRXstudent GET success");
            console.info("SWPWRXstudent GET data",data);
            console.info("SWPWRXstudent GET msg",msg);

            var data_obj = JSON.parse(data);
            console.info("SWPWRXstudent GET data_obj",data_obj);

            // Set our context variables from the data we receive
            var question = data_obj.question;
            var grade = data_obj.grade;
            var solution = data_obj.solution;
            var count_attempts = data_obj.count_attempts;
            var variants_count = data_obj.variants_count;
            var max_attempts = data_obj.max_attempts;
            // var enable_showme = question.q_option_showme;
            // var enable_hint = question.q_option_hint;
            var weight = question.q_weight;
            var min_steps = question.q_grade_min_steps_count;
            var min_steps_ded = question.q_grade_min_steps_ded;
            var swpwr_problem = question.swpwr_problem;
            var swpwr_id = question.q_id;
            var swpwr_rank = question.q_swpwr_rank;
            var swpwr_invalid_schemas = question.q_swpwr_invalid_schemas;
            var swpwr_problem_hints = question.q_swpwr_problem_hints;

            console.info("SWPWRXStudent question ID",swpwr_id);
            console.info("SWPWRXStudent question",question);
            console.info("SWPWRXStudent swpwr_problem",swpwr_problem);
            // console.info("SWPWRXStudent enable_showme",enable_showme);
            // console.info("SWPWRXStudent enable_hint",enable_hint);
            console.info("SWPWRXStudent solution",solution);
            console.info("SWPWRXStudent count_attempts",count_attempts);
            console.info("SWPWRXStudent variants_counnt",variants_count);
            console.info("SWPWRXStudent max_attempts",max_attempts);
            console.info("SWPWRXStudent weight ",weight);
            console.info("SWPWRXStudent min steps",min_steps);
            console.info("SWPWRXStudent min steps dec",min_steps_ded);
            console.info("SWPWRXStudent grade",grade);
            // console.info("SWPWRXStudent swpwr_id",swpwr_id);
            console.info("SWPWRXStudent swpwr_rank ",swpwr_rank);
            console.info("SWPWRXStudent swpwr_invalid_schemas ",swpwr_invalid_schemas);
            console.info("SWPWRXStudent swpwr_problem_hints ",swpwr_problem_hints);

            /* PAGE LOAD EVENT */
            $(function ($) {
            });
        } // end of success block
    });
    console.info("SWPWRXStudent end");
}
