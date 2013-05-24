DW.get_is_user = function () {
    var users = new Array();
    users["ids"] = [];
    users["names"] = [];
    $('.datasenders_list .is_user:checked').each(function () {
        users["ids"].push($(this).val());
        users["names"].push($(this).parent().next().html());
    });

    return users;
}

DW.uncheck_all_users = function () {
    $(".datasenders_list .is_user").attr("checked", false);
}

DW.action_enabled = false;

$(document).ready(function () {
    var kwargs = {container:"#delete_all_ds_are_users_warning_dialog",
        cancel_handler:function () {
//            $("#action").val("");
            $('#action').removeAttr("clicked");
            $("input.is_user").attr("checked", false);
        },
        height:150,
        width:550
    }

    var delete_all_ds_are_users = new DW.warning_dialog(kwargs);

    function updateIds() {
        var allIds = [];
        $('.datasenders_list :checked').each(function () {
            allIds.push($(this).val());
        });
        return allIds;
    }

    function updateIdsNotUsers() {
        DW.uncheck_all_users();
        return updateIds();
    }

    $("#all_project_block").dialog({
        autoOpen:false,
        modal:true,
        title:gettext('Select Projects'),
        zIndex:1100,
        beforeClose:function () {
            $('#action').at;
        }
    });
    $("#web_user_block").dialog({
        autoOpen:false,
        modal:true,
        title:gettext('Give Web Submission Access'),
        zIndex:1100,
        width:900,
        beforeClose:function () {
//            $('#action').val('');
            $('#action').removeAttr("clicked");
            $('#web_user_error').hide();
        }
    });

    $("#all_project_block .cancel_link").bind("click", function () {
        $("#all_project_block").dialog("close");
    });

    $("#web_user_block .cancel_link").bind("click", function () {
        $("#web_user_block").dialog("close");
    });

    $("#all_project_block .button").bind("click", function () {
        $('#error').remove();
        var allIds = updateIds();
        var projects = [];
        $('#all_project_block :checked').each(function () {
            projects.push($(this).val());
        });
        if (projects.length == 0) {
            $('<div class="message-box" id="error">' + gettext("Please select atleast 1 Project")
                + '</div>').insertBefore($("#all_projects"));
        } else {
            var url = '/entity/' + $('#action').attr("clicked") + '/';
            $.blockUI({ message:'<h1><img src="/media/images/ajax-loader.gif"/><span class="loading">'
                + gettext("Just a moment") + '...</span></h1>', css:{ width:'275px', zIndex:1000000}});
            $.post(url,
                {'ids':allIds.join(';'), 'project_id':projects.join(';')}
            ).success(function (data) {
                    window.location.href = data;
                });
        }
    });

    function populate_dialog_box_for_web_users() {
        var data_sender_details = [];
        $('.datasenders_list :checked').each(function () {
            var row = $(this).parent().parent();
            var data_sender = {};
            data_sender.short_name = $($(row).children()[2]).html();
            data_sender.name = $($(row).children()[1]).html();
            data_sender.location = $($(row).children()[4]).html();
            data_sender.contactInformation = $($(row).children()[6]).html();
            data_sender.email = $($(row).children()[7]).html();
            data_sender.input_field_disabled = "disabled";
            if ($.trim(data_sender.email) == "--") {
                data_sender.input_field_disabled = "";
                data_sender.email = "";
            }
            data_sender_details.push(data_sender);
        });
        $('#web_user_table_body').html($.tmpl('webUserTemplate', data_sender_details));
        $("#web_user_block").dialog("open");
    }

    $('#action li a').click(function (e) {
        var allIds = updateIds();
        if ($(this).parent().hasClass("disabled")) {
            e.preventDefault();
            return false;
        }
        var action = this.className;
        $("#action").attr("clicked", action);

        if (action == 'makewebuser') {
//            this.removeClass('dropdown-open').parents('.btn-group').removeClass('open');
            populate_dialog_box_for_web_users();
        
        } else if (action == "delete") {
            $(this).val('');
            $("#note_for_delete_users").hide();
            var users = DW.get_is_user();
            if (users["names"].length) {
                $("#checkall-datasenders").attr("checked", false);
                var users_list_for_html = "<li>" + users["names"].join("</li><li>") + "</li>";
                if (users["names"].length == allIds.length) { //Each DS selected is also User
                    $(delete_all_ds_are_users.container + " .users_list").html(users_list_for_html);
                    delete_all_ds_are_users.show_warning();
                } else { // A mix of Simple DS and DS having user credentials
                    $("#note_for_delete_users .users_list").html(users_list_for_html);
                    $("#note_for_delete_users").show();
                    allIds = updateIdsNotUsers();
                    warnThenDeleteDialogBox(allIds, "reporter", this);
                }
            } else {
                warnThenDeleteDialogBox(allIds, "reporter", this);
            }
        } else if (action == "edit") {
            location.href = '/entity/datasender/edit' + '/' + allIds[0] + '/';
        } else {
            $("#all_project_block").dialog("open");
        }
    });



    $('#web_user_button').click(function () {
        $('#web_user_error').hide();
        var post_data = [];
        var should_post = true;
        $('input:enabled.ds-email').each(function () {
            var email = $.trim($(this).val());
            var emailRegEx = /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}$/i;
            if (email == "") {
                $('#web_user_error').html(gettext('Emails are mandatory'));
                $('#web_user_error').removeClass('none');
                $('#web_user_error').show();
                should_post = false;
                return false;
            }
            if ($.trim(email).search(emailRegEx) == -1) {
                $('#web_user_error').removeClass('none');
                $('#web_user_error').html(email + gettext(": is not a valid email"));
                $('#web_user_error').show();
                should_post = false;
                return false;
            }
            var reporter_id = $($(this).parent().parent().children()[0]).html();
            post_data.push({email:email, reporter_id:reporter_id});
        });
        if (!should_post || post_data.length == 0) {
            return;
        }
        $.blockUI({ message:'<h1><img src="/media/images/ajax-loader.gif"/><span class="loading">'
            + gettext("Just a moment") + '...</span></h1>', css:{ width:'275px', zIndex:1000000}});
        $.post('/entity/webuser/create', {post_data:JSON.stringify(post_data)},
            function (response) {
                $.unblockUI();
                var json_data = JSON.parse(response);
                if (json_data.success) {
                    $("#web_user_block").dialog("close");
                    var redirect_url = location.href;
                    if (redirect_url.indexOf('?web=1') == -1) {
                        redirect_url = redirect_url + '?web=1';
                    }
                    window.location.href = redirect_url;
                } else {
                    var html = "";
                    var i = 0;
                    for (i; i < json_data.errors.length; i = i + 1) {
                        var email_in_error = json_data.errors[i].split(' ')[3];
                        var error_message = gettext('User with email ') + email_in_error + gettext(' already exists');
                        html += "<tr><td>" + error_message + "</td></tr>";
                    }
                    if (html != "") {
                        html = '<table cellpadding="0" cellspacing="0" border="0">' + html + '</table>';
                    }
                    $('#web_user_error').removeClass('none');
                    $('#web_user_error').html(html);
                    $('#web_user_error').show();
                }

            });
        return false;
    });

    var markup = "<tr><td>${short_name}</td><td>${name}</td><td style='width:150px;'>" +
        "${location}</td><td>${contactInformation}</td><td>" +
        "<input type='text' style='width:150px' class='ds-email' value='${email}' " +
        "${input_field_disabled}/></td></tr>";
    $.template("webUserTemplate", markup);

    $("#checkall-datasenders").bind("click", function(){
        var checked = $(this).attr("checked") == "checked";
        $("#all_data_senders tr td:first-child input:checkbox").attr("checked", checked);

        var action_dropdown = get_action_dropdown_object();
        if (!checked) {
            action_dropdown.deactivate_action();
        } else {
            action_dropdown.update_edit_action();
        }
    });

    $("#all_data_senders tr td:first-child input:checkbox").bind("click", function(){
        $("#checkall-datasenders").attr("checked", $('#all_data_senders input:checkbox').length == $('#all_data_senders input:checkbox[checked]').length);
    });

    function get_action_dropdown_object() {
        if ($("#associated_data_senders").length) {
            return DW.registered_ds_action_dropdown;
        } else {
            return DW.all_ds_action_dropdown
        }
    }

    var handle_results = function(data) {
        var right_mark = '<img alt="Yes" src="/media/images/right_icon.png">'
        template = "<tr><td><input type='checkbox'></td>"
        for(i =0; i<10; i++ ) template += "<td></td>";
        template +="</tr>";

        $("#checkall-datasenders").removeAttr('checked')
        $('#all_data_senders tr').remove();
        for(i=0; i<data.length; i++)  $('#all_data_senders').append(template)

        $('#all_data_senders tr').each(function(i, tr){
           $(tr).find('td input[type=checkbox]').val(data[i].short_code)
           $(tr.children[1]).text(data[i].name)
           $(tr.children[2]).text(data[i].short_code)
           $(tr.children[3]).text(data[i].location)
           $(tr.children[4]).text(data[i].gps)
           $(tr.children[5]).text(data[i].mobile_number)
           $(tr.children[6]).text(data[i].projects)
           $(tr.children[7]).text(data[i].email)

           $(tr.children[8]).html(right_mark)
           $(tr.children[9]).html(data[i].devices_web?right_mark:'--')
           $(tr.children[10]).html(data[i].devices_web?right_mark:'--')
        });

        $('#all_data_senders input[type=checkbox]').click(function() {
            var action_dropdown = get_action_dropdown_object();
            if ($('#all_data_senders input:checkbox[checked]').length==0) {
                action_dropdown.deactivate_action();
            } else {
                action_dropdown.init_action_dropdown();
            }

            $("#checkall-datasenders").attr("checked", $('#all_data_senders input:checkbox').length == $('#all_data_senders input:checkbox[checked]').length);
        })

    }

    $('#search').click(function() {
        $.post('/entity/datasenders/search', {'q':$('#q').val()}, handle_results, "json")
    })
});

