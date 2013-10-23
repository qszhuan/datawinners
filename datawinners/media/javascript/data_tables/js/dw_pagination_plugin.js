$.fn.dataTableExt.oPagination.dw_pagination = {
    "fnInit": function (oSettings, nPaging, fnCallbackDraw) {
        nPrevious = document.createElement('span');
        nNext = document.createElement('span');
        nMore = document.createElement('span');

        //nPrevious.appendChild(document.createTextNode(oSettings.oLanguage.oPaginate.sPrevious));
        nNext.appendChild(document.createTextNode(oSettings.oLanguage.oPaginate.sNext));
        $(nPrevious).html("&#x25C0;")
        $(nNext).html("&#x25B6;")
        $(nMore).html('<span>&#x25BE;</span>')

        var instance_id = parseInt(Math.random() * 100);
        dropdown_id = "pagination_more_menu" + instance_id;
        dropdown = document.createElement("div");
        dropdown.setAttribute("id", dropdown_id);
        dropdown.setAttribute("class", "dropdown dropdown-tip");
        first_page_id = "first_page" + instance_id;
        last_page_id = "last_page" + instance_id;
        dropdown.innerHTML = '<ul class="dropdown-menu"> <li> <a href="#" id=' + first_page_id + '>' + gettext('First') + '</a> </li> <li> <a  id=' + last_page_id + '>' + gettext('Last') + '</a></li>';

        nPrevious.className = "paginate_button previous";
        nNext.className = "paginate_button next";
        nMore.className = "paginate_more";

        nPaging.appendChild(nPrevious);
        nPaging.appendChild(nNext);
        nPaging.appendChild(nMore);
        nPaging.appendChild(dropdown);


        $(nMore).dropdown('attach', "#" + dropdown_id);

        $(nPrevious).click(function () {
            if ($(this).attr('class').indexOf("disabled")<0){
                oSettings.oApi._fnPageChange(oSettings, "previous");
                fnCallbackDraw(oSettings);
            }
        });

        $(nNext).click(function () {
            if ($(this).attr('class').indexOf("disabled")<0){
                oSettings.oApi._fnPageChange(oSettings, "next");
                fnCallbackDraw(oSettings);
            }
        });

        $(nPaging).find("#"+first_page_id).click(function(){
             if (!$(this).parent().hasClass("disabled")){
                oSettings.oApi._fnPageChange(oSettings, "first");
                fnCallbackDraw(oSettings);
                 return true;
             }
            return false;
        });

        $(nPaging).find("#"+last_page_id).click(function(){
             if (!$(this).parent().hasClass("disabled")){
                oSettings.oApi._fnPageChange(oSettings, "last");
                fnCallbackDraw(oSettings);
                return true;
             }
            return false;
        });

        /* Disallow text selection */
        $(nPrevious).bind('selectstart', function () {
            return false;
        });
        $(nNext).bind('selectstart', function () {
            return false;
        });
    },


    "fnUpdate": function (oSettings, fnCallbackDraw) {
        if (!oSettings.aanFeatures.p) {
            return;
        }

        /* Loop over each instance of the pager */
        var an = oSettings.aanFeatures.p;
        for (var i = 0, iLen = an.length; i < iLen; i++) {
            var buttons = an[i].getElementsByTagName('span');
            if (oSettings._iDisplayStart === 0) {
                buttons[0].className = "paginate_disabled_previous";
                $($(an[i]).find("ul.dropdown-menu>li")[0]).addClass('disabled')

            }
            else {
                buttons[0].className = "paginate_enabled_previous";
                $($(an[i]).find("ul.dropdown-menu>li")[0]).removeClass('disabled')
            }

            if (oSettings.fnDisplayEnd() == oSettings.fnRecordsDisplay()) {
                buttons[1].className = "paginate_disabled_next";
                $($(an[i]).find("ul.dropdown-menu>li")[1]).addClass('disabled')
            }
            else {
                buttons[1].className = "paginate_enabled_next";
                $($(an[i]).find("ul.dropdown-menu>li")[1]).removeClass('disabled')
            }

            if (oSettings._iDisplayStart === 0 && oSettings.fnDisplayEnd() == oSettings.fnRecordsDisplay()) {
                buttons[2].className = "paginate_more_disabled dropdown-disabled";
            } else {
                buttons[2].className = "paginate_more";
            }
        }
    }
};