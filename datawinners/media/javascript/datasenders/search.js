$(function(){
    var handle_results = function(data) {
        var right_mark = '<img alt="Yes" src="/media/images/right_icon.png">'
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
    }

    $('#search').click(function() {
        $.post('/entity/datasenders/search', {'q':$('#q').val()}, handle_results, "json")
    })
})