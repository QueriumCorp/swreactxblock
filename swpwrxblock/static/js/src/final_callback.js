
      // global array for storing the SWPWR problems in the assignment

      //NOTYET window.swpwr_problems = [];

      // Final callback to submit SWPWR React app results

//NOTYET      returnPowerResults(solution){
//NOTYET        console.info("returnPowerResults solution",solution);
//NOTYET        var solution_string = JSON.stringify(solution);
//NOTYET        console.info("returnPowerResults solution string",solution_string);
//NOTYET        $.ajax({
//NOTYET          type: "POST",
//NOTYET          url: handlerUrlSwpwrResults,
//NOTYET          data: solution_string,
//NOTYET          success: function (data,msg) {
//NOTYET            console.info("returnPowerResults solution POST success");
//NOTYET            console.info("returnPowerResults solution POST data",data);
//NOTYET            console.info("returnPowerResults solution POST ",msg);
//NOTYET          },
//NOTYET          error: function(XMLHttpRequest, textStatus, errorThrown) {
//NOTYET            console.info("returnPowerResults solution POST error textStatus=",textStatus," errorThrown=",errorThrown);
//NOTYET          }
//NOTYET        });
//NOTYET        // Hide the React app and show the problem complete msg
//NOTYET        $('.SWPowerComponent').hide();  // Hide React app root div
//NOTYET        $('.problem-complete').show();  // Show the 'problem is complete' message
//NOTYET        $('.sequence-bottom').show();   // Show the problem navigation buttons again
//NOTYET      };
