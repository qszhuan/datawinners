(function($) {
$.fn.dwTable = function(options){
        function continue_dwtable_creation(){
            var defaults = {
                "concept":"Row",
                "sDom": "ipfrtipl",
                "bProcessing": true,
                "aLengthMenu": [10, 25, 50, 100],
                "iDisplayLength": 25,
                "bResetDisplay": true,
                "sAjaxDataProp": "data",
                "sPaginationType": "dw_pagination",
                "fnServerData": function (sSource, aoData, fnCallback, oSettings) {
                    lastXHR = oSettings.jqXHR;
                    lastXHR && lastXHR.abort && lastXHR.abort();
                    aoData.push({"name":"disable_cache","value":new Date().getTime()});
                    oSettings.jqXHR = $.ajax({
                        "dataType": 'json',
                        "type": "GET",
                        "url": sSource,
                        "data": aoData,
                        "success": function (result) {
                            $.each(result.data, function (i, data) {
                                data.unshift('')
                            });
                            fnCallback(result);
                        },
                        "error": function () {
                        },
                        "global": false
                    });
                },
                "searchPlaceholderText":'Enter any information you want to find'
            }
            $.extend(defaults, options);
            defaults["oLanguage"] = defaults["oLanguage"] || {};
            $.extend(defaults["oLanguage"],{
                            "sInfoFiltered": "",
                            "sLengthMenu": gettext("Show") + " _MENU_ " + gettext(defaults.concept),
                            "sProcessing": "<img class=\"search-loader\"src=\"/media/images/ajax-loader.gif\"></img>",
                            "sInfo": interpolate(gettext("<b>%(start)s to %(end)s</b> of %(total)s %(subject_type)s(s)"),
                                {'start': '_START_', 'end': '_END_', 'total': '_TOTAL_', subject_type:defaults.concept}, true),
                            "sInfoEmpty": gettext("<b> 0 to 0</b> of 0") + " " + gettext(defaults.concept),
                            "sSearch": "<strong>" + gettext("Search:") + "</strong>"
                            ,"sZeroRecords": gettext("No matching records found")
                         });

            defaults["aoColumns"] && defaults["aoColumns"].unshift({"sTitle": "<input type='checkbox' class='checkall-checkbox'/>"});

            defaults["aoColumnDefs"] = defaults["aoColumnDefs"] || [];

            if (typeof defaults["actionItems"] != "undefined"){
                defaults["aoColumnDefs"].push({ "sTitle": "<input type='checkbox' class='checkall-checkbox'></input>", "fnRender": function (data)
                {
                    return '<input type="checkbox" class="row_checkbox" value="' + data.aData[options.sAjaxDataIdColIndex] + '"/>';
                }, "aTargets": [0] });
                defaults["aoColumnDefs"].push({"bSortable": false, "aTargets": [0]});
            }

            defaults["fnPreDrawCallback"] = function(oSettings) {
                $(this).find("input:checked").attr('checked',false);
            };

            defaults["fnDrawCallback"] = function (oSettings) {
                $(this).find("thead input:checkbox").attr("disabled", oSettings.fnRecordsDisplay() == 0);
                var nCols = $(this).find('thead>tr').children('th').length;
                $(this).find('tbody').prepend('<tr style="display:none;"><td class ="table_message" colspan=' + nCols+ '><div class="select_all_message"></div></td></tr>');
            }


            defaults["fnInitComplete"] = function(original_init_complete_handler, concept, actionItems){
                return function(){
                    var dataTableObject = this;

                    if (typeof actionItems != "undefined" && actionItems.length){
                        //$(dataTableObject).find('thead>tr').prepend('<th><input type="checkbox" class="checkall-checkbox"></th>');
                        var dropdown_id = "dropdown-menu" + Math.floor(Math.random() * 10000000000000001);
                        var html = '<div class="table_action_button action_bar clear-both"> <div class="btn-group">' +
                                '<button class="btn dropdown-toggle action" href="#" data-dropdown="#'+dropdown_id+ '">Actions' +
                                '<span class="caret"></span> </button> </div></div>';
                        var action_button = $(dataTableObject).parents(".dataTables_wrapper").find(".dataTables_info").before($(html));
                        var select_link_text = interpolate(gettext("Select a %(concept)s"), {"concept":concept}, true);
                        $(this).parents(".dataTables_wrapper").append('<div id="'+ dropdown_id + '" class="dropdown"> <ul class="dropdown-menu"><li class="none-selected disabled"><label>' + select_link_text + '</label><li></ul> </div>');

                        $(".checkall-checkbox").parents("th").addClass("checkbox_col");
                        //$(action_button).dropdown();



                        for (var item = 0; item<actionItems.length; item++) {
                            var item_handler = function(handler){
                               return  function(e) {
                                    if ($(this).hasClass("disabled")){
                                        e.preventDefault();
                                        return false;
                                    }
                                   var all_selected =  $(dataTableObject).find(".select_all_message").data('all_selected');
                                   var selected_ids = $.map($(dataTableObject).find("input.row_checkbox:checked"), function(e) {return $(e).val()});
                                   return handler(dataTableObject, selected_ids, all_selected);
                                };
                            };
                            var menu_item = $('<li class="'+ actionItems[item].allow_selection +'"><a class="'  + actionItems[item].label.toLowerCase() + '">' + gettext(actionItems[item].label) + '</a></li>');
                            var a = $("#" + dropdown_id + ">.dropdown-menu").append(menu_item);
                            $(menu_item, 'a').click(item_handler(actionItems[item].handler));
                        }

                        //$(dataTableObject).find(".action").dropdown();
                        //$(dataTableObject).find(".action").dropdown("attach", "#" + dropdown_id)

                        $(this).parents(".dataTables_wrapper").find('.action').click(function(){
                            var selected_count = $(this).parents('.dataTables_wrapper').find('input:checked').not(".checkall-checkbox").length
                            if(selected_count == 0){
                                $("#" + dropdown_id + ">.dropdown-menu li").hide();
                                $("#" + dropdown_id + ">.dropdown-menu li.none-selected").show();
                            } else {
                                $("#" + dropdown_id + ">.dropdown-menu li").show();
                                $("#" + dropdown_id + ">.dropdown-menu li.none-selected").hide();
                                if (selected_count>1)
                                    $("#" + dropdown_id + ">.dropdown-menu li.single").addClass('disabled')
                                else
                                    $("#" + dropdown_id + ">.dropdown-menu li.single").removeClass('disabled')
                            }
                        });
                    }

                    function clear_select_all_rows() {
                        $(dataTableObject).find(".select_all_message").data('all_selected', false);
                        $(dataTableObject).find('input:checked').attr('checked', false);
                        $(dataTableObject).find(".select_all_message").html('');
                        $(dataTableObject).find(".select_all_message").parents('tr').hide();
                    }

                    function select_all_rows() {
                        $(dataTableObject).find(".select_all_message").data('all_selected', true);
                        var total_number_of_records = $(dataTableObject).dataTable().fnSettings().fnRecordsDisplay();
                        var msg = interpolate(gettext("You have selected all %(total_number_of_records)s %(concept)s(s)."), {"total_number_of_records":total_number_of_records,"concept": concept}, true);
                        msg  += ' <a href="#">' + gettext("Clear Selection") + '</a>';
                        $(dataTableObject).find(".select_all_message").html(msg);
                        $(dataTableObject).find(".select_all_message").find('a').click(clear_select_all_rows);
                    }

                    function show_select_all_message(show){
                        var show = $(dataTableObject).find(".checkall-checkbox").is(":checked");
                        boxes = $(dataTableObject).find("input.row_checkbox")
                        var total_number_of_records = $(dataTableObject).dataTable().fnSettings().fnRecordsDisplay();
                        var are_there_more_items = (boxes.length != total_number_of_records);
                        if(show && are_there_more_items) {
                            var msg = "";
                            $(dataTableObject).find(".table_message").parent().show();
                            msg = interpolate(gettext("You have selected <b>%(number_of_records)s</b> %(concept)s(s) on this page."), {"number_of_records": boxes.length, "concept": concept}, true);
                            msg += ' <a href="#">' +  interpolate(gettext('Select all <b> %(total_number_of_records)s </b>%(concept)s(s)'),
                                    {'total_number_of_records': total_number_of_records, "concept": concept}, true) + "</a>";
                            var link = $(msg)
                            $(dataTableObject).find(".select_all_message").html(msg);
                            $(dataTableObject).find(".select_all_message").find('a').click(select_all_rows);
                        } else {
                            $(dataTableObject).find(".table_message").parent().hide();
                            $(dataTableObject).find(".select_all_message").html('')
                        }
                    }


                    $(this).find(".checkall-checkbox").click(function(){
                        $(dataTableObject).find("input.row_checkbox").attr('checked', $(this).is(":checked"));
                        show_select_all_message();
                    });

                    $(this).on('click', ".row_checkbox", function(){
                        boxes = $(dataTableObject).find("input.row_checkbox")
                        all_checked = boxes.length == boxes.filter(":checked").length
                        $(dataTableObject).find(".checkall-checkbox").attr('checked', all_checked);
                        show_select_all_message();

                    });

                    try {
                        $(dataTableObject).parents(".dataTables_wrapper").find(".dataTables_filter input").attr('placeholder', gettext(defaults.searchPlaceholderText));
                    } catch(ignore){} //fails on old IEs

                    if (typeof original_init_complete_handler == "function") original_init_complete_handler.apply(this, arguments);
                }
            }(defaults["fnInitComplete"], defaults.concept, defaults.actionItems);


            $(this).dataTable(defaults)["_dw"] = defaults;
            $(this, "table").wrap('<div class="table_wrapper"></div>');

        }

         if($(this).find('th').length == 0 && typeof options["aoColumns"] == "undefined") {
            $.ajax({"dataType": 'json',
                    "type": "GET",
                    "url": options.sAjaxSource,
                    "data": {"header":true},
                    "success":function(){
                        continue_dwtable_creation();
                    }});
        }else {
             continue_dwtable_creation.apply(this, arguments);
         }
    };
})(jQuery);

$.fn.dataTableExt.oApi.fnReloadAjax = function ( oSettings, sNewSource, fnCallback, bStandingRedraw )
{
    if ( sNewSource !== undefined && sNewSource !== null ) {
        oSettings.sAjaxSource = sNewSource;
    }

    // Server-side processing should just call fnDraw
    if ( oSettings.oFeatures.bServerSide ) {
        oSettings["iInitDisplayStart"] = oSettings._iDisplayStart;
        this.fnDraw(false);
        return;
    }

    this.oApi._fnProcessingDisplay( oSettings, true );
    var that = this;
    var iStart = oSettings._iDisplayStart;
    var aData = [];

    this.oApi._fnServerParams( oSettings, aData );

    oSettings.fnServerData.call( oSettings.oInstance, oSettings.sAjaxSource, aData, function(json) {
        /* Clear the old information from the table */
        that.oApi._fnClearTable( oSettings );

        /* Got the data - add it to the table */
        var aData =  (oSettings.sAjaxDataProp !== "") ?
            that.oApi._fnGetObjectDataFn( oSettings.sAjaxDataProp )( json ) : json;

        for ( var i=0 ; i<aData.length ; i++ )
        {
            that.oApi._fnAddData( oSettings, aData[i] );
        }

        oSettings.aiDisplay = oSettings.aiDisplayMaster.slice();

        that.fnDraw();

        if ( bStandingRedraw === true )
        {
            oSettings._iDisplayStart = iStart;
            that.oApi._fnCalculateEnd( oSettings );
            that.fnDraw( false );
        }

        that.oApi._fnProcessingDisplay( oSettings, false );

        /* Callback user function - for event handlers etc */
        if ( typeof fnCallback == 'function' && fnCallback !== null )
        {
            fnCallback( oSettings );
        }
    }, oSettings );
};
