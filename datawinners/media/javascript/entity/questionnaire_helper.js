//DW is the global name space for DataWinner

DW.instruction_template = {
    "number":gettext("Answer must be a number."),
    "min_number":gettext("Answer must be a number. The minimum is %d."),
    "max_number":gettext("Answer must be a number. The maximum is %d."),
    "range_number":gettext("Answer must be a number between %d-%d."),
    "text":gettext("Answer must be a word"),
    "max_text":gettext("Answer must be a word %d characters maximum"),
    "date":gettext("Answer must be a date in the following format: %s. Example: %s"),
    "single_select":gettext("Choose 1 answer from the list. Example: a"),
    "multi_select":gettext("Choose 1 or more answers from the list. Example: a or ab "),
    "gps":gettext("Answer must be GPS co-ordinates in the following format: xx.xxxx,yy.yyyy Example: -18.1324,27.6547 "),
    "dd.mm.yyyy":"25.12.2011",
    "mm.dd.yyyy":"12.25.2011",
    "mm.yyyy":"12.2011"

};
DW.date_template = {
    "dd.mm.yyyy":gettext("day.month.year"),
    "mm.dd.yyyy":gettext("month.day.year"),
    "mm.yyyy":gettext("month.year")

};
DW.question = function (question) {
    var question_name = DW.next_question_name_generator();
    var defaults = {
        name:question_name,
        code:"code",
        required:true,
        type:"text",
        language:'en',
        choices:[],
        entity_question_flag:false,
        length_limiter:"length_unlimited",
        length:{
            min:1,
            max:""
        },
        range:{
            min:"",
            max:""
        },
        label:{
            en:"Question",
            fr:"Question"
        },
        date_format:"mm.yyyy",
        instruction:gettext("Answer must be a text"),
        newly_added_question:false,
        event_time_field_flag:false
    };

    // Extend will override the default values with the passed values(question), And take the values from defaults when its not present in question
    //first argument "true" in extend field shows that appent values in default
    this.options = $.extend(true, defaults, question);
    this._init();
};

DW.initChoices = function (choices) {
    var final_choices = [];
    $.each(choices, function (index, choice) {
        var display_choice = {};
        display_choice['text'] = choice.text;
        display_choice['val'] = choice.val;
        display_choice['id'] = choice.id;
        final_choices.push(display_choice);
    });
    return final_choices;
};

DW.question.prototype = {
    _init:function () {
        var q = this.options;
        this.newly_added_question = ko.observable(q.newly_added_question);
        this.range_min = ko.observable(q.range.min);
        this.event_time_field_flag = ko.observable(q.event_time_field_flag);

        //This condition required especially because in DB range_max is a mandatory field
        this.range_max = ko.observable(q.range.max);

        this.min_length = ko.observable(q.length.min);
        this.max_length = ko.observable(q.length.max);
        if (DW.isRegistrationQuestionnaire()) {
            this.name = ko.observable(q.name);
            this.title = ko.observable(q.label);
        } else {
            this.title = ko.observable(q.name);
        }
        this.code = ko.observable(q.code);
        this.type = ko.observable(q.type);
        this.required = ko.observable(q.required);

        var initialValues = DW.initChoices(q.choices);
        this.choices = ko.observableArray(initialValues);
        this.is_entity_question = ko.observable(q.entity_question_flag);
        this.date_format = ko.observable(q.date_format);
        this.length_limiter = ko.observable(q.length.max ? "length_limited" : "length_unlimited");
        this.instruction = ko.dependentObservable({
            read:function () {
                if (this.type() == "text") {
                    if (this.max_length() != "" && this.max_length() > 0) {
                        return $.sprintf(DW.instruction_template.max_text, this.max_length());
                    }
                    return DW.instruction_template.text;
                }
                if (this.type() == "telephone_number") {
                    return $.sprintf(DW.instruction_template.max_text, "15");
                }
                if (this.type() == "list") {
                    return DW.instruction_template.text;
                }
                if (this.type() == "integer") {
                    if (this.range_min() == "" && this.range_max() == "") {
                        return DW.instruction_template.number;
                    }
                    if (this.range_min() == "") {
                        return $.sprintf(DW.instruction_template.max_number, this.range_max());
                    }
                    if (this.range_max() == "") {
                        return $.sprintf(DW.instruction_template.min_number, this.range_min());
                    }
                    return $.sprintf(DW.instruction_template.range_number, this.range_min(), this.range_max());
                }
                if (this.type() == "date") {
                    return $.sprintf(DW.instruction_template.date, DW.date_template[this.date_format()], DW.instruction_template[this.date_format()]);
                }
                if (this.type() == "geocode") {
                    return DW.instruction_template.gps;
                }
                if (this.type() == "select1") {
                    return DW.instruction_template.single_select;
                }
                if (this.type() == "select") {
                    return DW.instruction_template.multi_select;
                }
                return "No instruction can be generated";
            },
            owner:this
        });
        this.canBeDeleted = function () {
            if (DW.isRegistrationQuestionnaire()) {
                return (!this.is_entity_question() && this.name() != 'name');
            } else {
                return (!this.is_entity_question());
            }
        };
        this.isEnabled = function () {
            return this.newly_added_question();
        };


        this.isAChoiceTypeQuestion = ko.dependentObservable({
            read:function () {
                return this.type() == "select" || this.type() == "select1" ? "choice" : "none";
            },
            write:function (value) {
                this.type(this.type() == "" ? "select" : "select1");
            },
            owner:this
        });
    }

};


DW.change_question_title_for_reporting_period = function (replaceto, replacewith) {
    $(questionnaireViewModel.questions()).each(function (question) {
        if (questionnaireViewModel.selectedQuestion().event_time_field_flag()) {
            var question_title = questionnaireViewModel.selectedQuestion().title();
            questionnaireViewModel.selectedQuestion().title(question_title.replace(replaceto, replacewith));
        }
    });
    questionnaireViewModel.questions.valueHasMutated();
};


DW.removeQuestionCheckForRegistration = function (question) {
    if (!DW.has_submission_delete_warning_for_entity.is_continue && DW.questionnaire_has_submission()) {
        DW.has_submission_delete_warning_for_entity.show_warning();
    } else {
        questionnaireViewModel.removeQuestion(question);
    }
};

DW.removeQuestionCheckForSubmission = function (question) {
    var index = $.inArray(question, questionnaireViewModel.questions());
    if (questionnaireViewModel.questions()[index].event_time_field_flag()) {
        DW.delete_periodicity_question_warning.show_warning();
    } else if (is_edit && !DW.has_submission_delete_warning.is_continue && !question.newly_added_question() && DW.questionnaire_has_submission()) {
        DW.has_submission_delete_warning.show_warning();
    }else{
        questionnaireViewModel.removeQuestion(question);
    }
};

DW.isRegistrationQuestionnaire = function () {
    return $('#qtype').val() == 'subject';
};

DW.next_question_name_generator = function () {
    return 'Question ' + ($('div.question_list ol li').length + 1);
};

DW.next_option_value = function (lastChoice) {
    var nextOption = "a";
    if (lastChoice.charCodeAt(lastChoice.length - 1) == 122) {
        if (lastChoice.length == 2) {
            nextOption = String.fromCharCode(lastChoice.charCodeAt(0) + 1) + "a";
        } else {
            nextOption = "1a";
        }
    } else {
        nextOption = (lastChoice.length == 2) ? lastChoice[0] : "";
        nextOption += String.fromCharCode(lastChoice.charCodeAt(lastChoice.length - 1) + 1);
    }
    return nextOption;
}

DW.report_period_date_format_change_warning = {
    old_date_format:"",
    is_continue:false,
    has_not_warning:true,
    init:function () {
        DW.report_period_date_format_change_warning.init_warning_dialog();
        DW.report_period_date_format_change_warning.bind_dialog_closed();
        DW.report_period_date_format_change_warning.bind_cancel_link();
        DW.report_period_date_format_change_warning.bind_continue();
    },
    init_warning_dialog:function () {
        $("#change_date_format_warning_message").dialog({
            title:gettext("Warning !!"),
            modal:true,
            autoOpen:false,
            height:200,
            width:400,
            closeText:'hide'
        });
    },

    bind_dialog_closed:function () {
        $("#change_date_format_warning_message").bind("dialogclose", function (event, ui) {
                if (!DW.report_period_date_format_change_warning.is_continue) {
                    var date_format = questionnaireViewModel.selectedQuestion().date_format();
                    $("input[value='" + date_format + "']").attr("checked", true);
                    DW.report_period_date_format_change_warning.is_continue = false;
                }
            }
        )
    },

    bind_cancel_link:function () {
        $("#change_date_format_cancel").bind("click", function () {
            var date_format = DW.report_period_date_format_change_warning.old_date_format;
            questionnaireViewModel.selectedQuestion().date_format(date_format);
            $("input[value='" + date_format + "']").attr("checked", true);
            DW.report_period_date_format_change_warning.is_continue = false;
            $("#change_date_format_warning_message").dialog("close");
        });

    },

    bind_continue:function () {
        $("#change_date_format_continue").bind("click", function () {
            DW.report_period_date_format_change_warning.is_continue = true;
            DW.report_period_date_format_change_warning.has_not_warning = false;
            $("#change_date_format_warning_message").dialog("close");
        });
    },

    show_warning:function () {
        $("#change_date_format_warning_message").dialog("open");
        DW.show_dialog_overlay();
        DW.report_period_date_format_change_warning.is_continue = false;
    }
};


DW.option_warning_dialog = {
    init:function () {
        DW.option_warning_dialog.continueEventHandler = function(){};
        DW.option_warning_dialog.cancelEventHandler = function(){};
        DW.option_warning_dialog.dialog_id = "#option_warning_message";
        DW.option_warning_dialog.init_warning_dialog();
        DW.option_warning_dialog.bind_cancel_link();
        DW.option_warning_dialog.bind_continue();
        DW.option_warning_dialog.bind_close();
    },
    init_warning_dialog:function () {
        $(DW.option_warning_dialog.dialog_id).dialog({
            title:gettext("Warning !!"),
            modal:true,
            autoOpen:false,
            height:'auto',
            width:500,
            closeText:'hide'
        });
    },
    bind_cancel_link:function () {
        $(DW.option_warning_dialog.dialog_id+"_cancel").bind("click", function () {
            $(DW.option_warning_dialog.dialog_id).dialog("close");
            DW.option_warning_dialog.cancelEventHandler();
            DW.hide_dialog_overlay();
        });
    },
    bind_close:function () {
        $('.ui-icon-closethick').bind("click", function () {
            $(DW.option_warning_dialog.dialog_id).dialog("close");
            DW.option_warning_dialog.cancelEventHandler();
            DW.hide_dialog_overlay();
        });
    },
    bind_continue:function () {
        $(DW.option_warning_dialog.dialog_id+"_continue").bind("click", function () {
            $(DW.option_warning_dialog.dialog_id).dialog("close");
            DW.option_warning_dialog.continueEventHandler();
            DW.hide_dialog_overlay();
        });
    },

    show_warning:function (message) {
        $("#option_warning_text")[0].innerHTML=message;
        $(DW.option_warning_dialog.dialog_id).dialog("open");
        DW.show_dialog_overlay();
    }
};
DW.change_date_format_for_reporting_period = function (date_format_element) {
    if (questionnaireViewModel.selectedQuestion().event_time_field_flag() && is_edit && DW.report_period_date_format_change_warning.has_not_warning) {
        DW.report_period_date_format_change_warning.show_warning();
    }
};

DW.change_option_text = function (choice, oldText,index) {
   DW.option_warning_dialog.show_warning(gettext("You have changed the text of your answer choice.<br>If you have previously collected data for this choice it will be replaced with the new text.<br><br>Are you sure you want to continue?"));
   DW.option_warning_dialog.cancelEventHandler = function(){
       choice.value = oldText;
       questionnaireViewModel.selectedQuestion().choices()[index].text=oldText;
       choice.focus();
   }
}

DW.close_the_tip_on_period_question = function(){
    if($("#question_title").hasClass("blue_frame")){
        $("#question_title").removeClass("blue_frame");
    }
    if($("#periode_green_message").length>0){
        $("#periode_green_message").hide();
    }
}

DW.questionnaire_has_submission = function(){
    var subject_questionnaire = (typeof(is_edit) == "undefined");
    if (subject_questionnaire){
        var entity_type = $("#entity-type").val();
        var url_get = $.sprintf("/alldata/entities/%s/", entity_type);
    } else {
        var form_code = $("#saved-questionnaire-code").val();
        var url_get = $.sprintf("/project/has_submission/%s/", form_code);
    }

    $.ajaxSetup({async:false});
    var return_value = true;
    $.blockUI({ message:'<h1><img src="/media/images/ajax-loader.gif"/><span class="loading">' + gettext("Just a moment") + '...</span></h1>', css:{ width:'275px'}});
    $.ajax({
        type:'GET',
        url:url_get,
        success:function (response) {
            $.ajaxSetup({async:true});
            $.unblockUI();
            
            if (subject_questionnaire) {
                return_value = response.length != 0;
            } else {
                var response_data = JSON.parse(response);
                return_value = response_data.has_data;
            }
        }
    });
    return return_value;
}


