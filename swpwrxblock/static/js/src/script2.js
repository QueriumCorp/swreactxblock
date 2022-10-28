      // Final callback to submit SWPWR React app results

      window.swpwr_onSubmit = (solution) =>{
        console.info("swpwr_onSubmit solution",solution);
        var solution_string = JSON.stringify(solution);
        console.info("swpwr_onSubmit solution string",solution_string);
        $.ajax({
          type: "POST",
          url: handlerUrlSwpwrResults,
          data: solution_string,
          success: function (data,msg) {
            console.info("swpwr_onSubmit solution POST success");
            console.info("swpwr_onSubmit solution POST data",data);
            console.info("swpwr_onSubmit solution POST ",msg);
          },
          error: function(XMLHttpRequest, textStatus, errorThrown) {
            console.info("swpwr_onSubmit solution POST error textStatus=",textStatus," errorThrown=",errorThrown);
          }
        });
      };

      // Template problem.  The Xblock code in swpwrxstudent.js will fill in values in this object.

      window.swpwr_problem = {
        label: "the problem label",
        description: "a desc",
        class: "sampleWord",
        stimulus: `A mountain bike is on sale for $399. Its regular price is $650. 
          What is the difference between the regular price and the sale price?`,
        stepsMnemonic: "POWER",
        steps: [
          // {
          //   label: "TEST",
          //   mnemonicIndex: 1,
          //   instruction: "Test Page",
          //   longInstruction: `This is a page to test components during development`,
          //   type: "TEST",
          //   valid: 0,
          // },
          {
            label: "Prepare",
            mnemonicIndex: 0,
            instruction: "Read the Problem",
            longInstruction: `Take two deep breaths. Read the word problem carefully. What is the 
            problem about? What does it ask you to find?`,
            type: "READ",
            valid: 1,
          },
          {
            label: "Prepare",
            mnemonicIndex: 0,
            instruction: "Identify Important Information",
            longInstruction: `Identify the key facts in the word problem below. Select 
            these important pieces of text. This will allow you to quickly paste helpful 
            snippets as you work the problem.`,
            type: "TAG",
            valid: 0,
          },
          {
            label: "Prepare",
            mnemonicIndex: 0,
            instruction: "What kind of problem is this?",
            longInstruction: `Discuss what type of problem you think this is. (Not graded)`,
            type: "DIAGRAMANALYZE",
            valid: 0,
          },
          {
            label: "Organize",
            mnemonicIndex: 1,
            instruction: "What type of problem is this?",
            longInstruction: `Select the problem type that best describes this problme`,
            type: "DIAGRAMSELECT",
            valid: 0,
          },
          {
            label: "Organize",
            mnemonicIndex: 1,
            instruction: "Fill in the Diagram",
            longInstruction: `Fill in each amount in the diagram with information from the problem. 
            You can click in each box and type the information using your keyboard, 
            or you can drag and drop the important information that you selected 
            earlier. If an amount is unknown, enter 'unknown'.`,
            type: "DIAGRAMMER",
            valid: 0,
          },
          // Alan's figma shows this as out of scope
          // {
          //   label: "Organize",
          //   mnemonicIndex: 1,
          //   instruction: "Setup the Equation",
          //   longInstruction: `Take your diagram and transform it into a math equation.`,
          //   type: "EQUATIONATOR",
          //   valid: 0,
          // },
          {
            label: "Work the Problem",
            mnemonicIndex: 2,
            instruction: "Solve the equation",
            longInstruction: `Take your diagram and transform it into a math equation.`,
            type: "STEPWISE",
            swlabel: "QUES-6011 YOY",
            // eslint-disable-next-line
            description:
              "Solve by addition, fool.  \\begin{array}{c}7x-2y=3 \\\\4x+5y=3.25\\end{array}", // eslint-disable-line
            definition: "SolveFor[7x-2y=3 && 4x+5y=3.25, {x,y}, EliminationMethod]",
            mathml: "\\(\\)",
            swtype: "gradeBasicAlgebra",
            hint1: "",
            hint2: "",
            hint3: "",
            valid: 0,
          },
          {
            label: "Explain",
            mnemonicIndex: 3,
            instruction: "Identify the Number and the Label ",
            longInstruction: `What is the number and what is its label ?`,
            type: "IDENTIFIER",
            valid: 0,
          },
          {
            label: "Explain",
            mnemonicIndex: 3,
            instruction: "Explain your Answer",
            longInstruction: `Answer the original question in plain language.`,
            type: "EXPLAINER",
            valid: 0,
          },
          {
            label: "Review",
            mnemonicIndex: 4,
            instruction: "Does your answer make sense?",
            longInstruction: `Discuss if your answer seems reasonable.`,
            type: "REVIEWER",
            valid: 0,
          },
        ],
      };
