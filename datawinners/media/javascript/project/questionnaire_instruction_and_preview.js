DW.instruction_and_preview = function (preview_url, preview_navigation_item) {
    this.preview_url = preview_url;
    this.preview_navigation_item = preview_navigation_item;
};

DW.instruction_and_preview.prototype = {
    bind_preview_navigation_item:function () {
        var that = this;
        $(this.preview_navigation_item).live('click', function () {
            if ($("#questionnaire_preview_instruction").css("display") == "none") {
                if (DW.questionnaire_form_validate()) {
                    that.load_preview_content();
                }
            }
            else
                that.load_preview_content();
        });
    },

    load_preview_content:function () {
        var post_data = this.get_post_data();

        var that = this;
        $.post(this.preview_url, post_data, function (response_data) {
            $("#questionnaire_content").html(response_data);
            $("#questionnaire_preview_instruction").show();
            $(".shadow-background").removeClass("shadow-background");
            $(that.preview_navigation_item).addClass("shadow-background");
            that.post_callback();
        }, 'html');
    },

    get_post_data: function(){
        return {'questionnaire-code':$('#questionnaire-code').val(),
            'question-set':JSON.stringify(ko.toJS(questionnaireViewModel.questions()), null, 2),
            'profile_form':basic_project_info.values(),
            'project_state':"Test"};
    },

    post_callback: function(){}
};

DW.web_instruction_and_preview = function () {};
DW.web_instruction_and_preview.prototype = new DW.instruction_and_preview(web_preview_link, '.navigation-web-preview');
DW.web_instruction_and_preview.prototype.post_callback = function () {
    $("#questionnaire_preview_instruction .help_icon").tooltip({
        position:"top right",
        relative:true,
        opacity:0.8,
        events:{
            def:"mouseover,mouseout",
            input:"focus,blur",
            widget:"focus mouseover,blur mouseout",
            tooltip:"click,click"
        }

    }).dynamic({ bottom:{ direction:'down', bounce:true } });
};

DW.smart_phone_instruction_and_preview = function () {};
DW.smart_phone_instruction_and_preview.prototype = new DW.instruction_and_preview(smart_phone_preview_link, '.navigation-smart-phone-preview');
DW.smart_phone_instruction_and_preview.prototype.get_post_data = function () {
    return {};
};

DW.instruction_and_preview.bind_cancel_button = function() {
    $(".close_preview").live('click', function() {
        $("#questionnaire_content").html("");
        $("#questionnaire_preview_instruction").hide();
        $(".shadow-background").removeClass("shadow-background");
    });
};

DW.instruction_and_preview.bind_print_button = function() {
    $(".printBtn").live('click', function() {
        var questionnaire = $(".sms-questionnaire").clone();
        questionnaire.addClass("sms-questionnaire");
        questionnaire.css("display:none");
        questionnaire.appendTo($("body"));
        window.print();
        questionnaire.remove();
        this.preventDefault();
    });
};

$(function () {
    DW.instruction_and_preview.bind_cancel_button();
    DW.instruction_and_preview.bind_print_button();
});