var sentence_id = 0
var image_clicked = false;

function restRequest(type, data, callback) {
    $.ajax({
       url: '/rest',
       type: type,
       contentType: 'application/json',
       data: JSON.stringify(data),
       success:function(data) { callback(data); },
       error: function (xhr, ajaxOptions, thrownError) { console.log(thrownError); }
    });
}

function remove_sentences(){
    var sentence_id =  document.getElementById("sentence_id").value;
    restRequest('POST', {'index':'remove_sentences', 'sentence_id':sentence_id}, show_info);
}

function true_positive(type, id, attack_uid){
    $("#sentence" + id).addClass('bg-warning');
    restRequest('POST', {'index':'true_positive', 'sentence_type':type, 'sentence_id':id, 'attack_uid':attack_uid}, show_info);
    sentenceContext(id, attack_uid)
}

function false_positive(type, id, attack_uid){
    document.getElementById("sentence-tid" + attack_uid.substr(attack_uid.length - 4)).remove();
    //$(`#sentence${id}`).removeClass('bg-warning');
    restRequest('POST', {'index':'false_positive', 'sentence_type':type, 'sentence_id':id, 'attack_uid':attack_uid}, show_info);
}

function false_negative_update(data){
    if (data.last == 'true') {
            $(`#sentence${data.id}`).removeClass('bg-warning');
    }
}

function deleteReport(report_id){
  if (confirm('Are you sure you want to delete this report?')) {
    restRequest('POST', {'index':'delete_report', 'report_id':report_id}, show_info)
    window.location.reload(true);
  } else {}

}

function false_negative(type, attack_uid){
    restRequest('POST', {'index':'false_negative', 'sentence_type':type, 'sentence_id':sentence_id, 'attack_uid':attack_uid}, show_info);
    alert(sentence_id)
}

function set_status(set_status, file_name){
    restRequest('POST', {'index':'set_status', 'set_status':set_status, 'file_name':file_name}, show_info);
}

function submit_report(){
    var url = document.getElementById("url").value;
    var title = document.getElementById("title").value;
    restRequest('POST', {'index':'insert_report', 'url':url, 'title':title}, show_info);
}

function show_dropdown() {
  document.getElementById("myDropdown").classList.toggle("show");
}

function filterFunction(input1, id1) {
  var input, filter, ul, li, a, i;
  input = document.getElementById(input1);
  filter = input.value.toUpperCase();
  div = document.getElementById(id1);
  a = div.getElementsByTagName("button");
  for (i = 0; i < a.length; i++) {
    txtValue = a[i].textContent || a[i].innerText;
    if (txtValue.toUpperCase().indexOf(filter) > -1) {
      a[i].style.display = "";
    } else {
      a[i].style.display = "none";
    }
  }
}

function show_info(data){
    console.log(data.status);
}

function savedAlert(){
    console.log("saved");
}

 function autoHeight() {
    if ($("html").height() < $(window).height()) {
      $("footer").addClass('sticky-footer');
    } else {
      $("footer").removeClass('sticky-footer');
    }
 }

function imageContext(data, attack_uid) {
  image_clicked = true;
  restRequest('POST', {'index':'image_context', 'uid':data, 'attack_uid':attack_uid}, updateImageContext);
  restRequest('POST', {'index':'confirmed_images', 'sentence_id': data}, updateConfirmedContext);
  sentence_id = data;
}

function updateImageContext(data) {
  $("#tableSentenceInfo tr").remove()
}

function sentenceContext(data, attack_uid){
    image_clicked = false;
    restRequest('POST', {'index':'sentence_context', 'uid': data, 'attack_uid':attack_uid}, updateSentenceContext);
    restRequest('POST', {'index':'confirmed_sentences', 'sentence_id': data}, updateConfirmedContext);
    sentence_id = data;
}

function updateSentenceContext(data){
    $("#tableSentenceInfo tr").remove()
    $.each(data, function(index, op){
        td1 = "<td><a href=https://attack.mitre.org/techniques/" + op.attack_tid + " target=_blank>" + op.attack_technique_name + "</a></td>"
        td2 = `<td><button class='btn btn-success' onclick='true_positive(true_positive, ${op.uid}, \"${op.attack_uid}\")'>Accept</button></td>`
        td3 = `<td><button class='btn btn-danger' onclick='false_positive(true_positive, ${op.uid}, \"${op.attack_uid}\")'>Reject</button></td>`
        tmp = `<tr id="sentence-tid${op.attack_uid.substr(op.attack_uid.length - 4)}">${td1}${td2}${td3}</tr>`
        $("#tableSentenceInfo").find('tbody').append(tmp);
    })
}

function updateConfirmedContext(data){
    $("#confirmedSentenceInfo tr").remove()
    $.each(data, function(index, op){
        td1 = "<td>" + op.name + "</td>"
        tmp = "<tr>" + td1 + "</tr>"
        $("#confirmedSentenceInfo").find('tbody').append(tmp);
    })
}

function divSentenceReload(){
    $('#sentenceContextSection').load(document.URL +  ' #sentenceContextSection');
}

function autoHeight() {
    if ($("html").height() < $(window).height()) {
      $("footer").addClass('sticky-footer');
    } else {
      $("footer").removeClass('sticky-footer');
    }
}

 // onDocumentReady function bind
$(document).ready(function() {
  $("header").css("height", $(".navbar").outerHeight());
  autoHeight();
});

// onResize bind of the function
$(window).resize(function() {
  autoHeight();
});

function addMissingTechnique(){
    uid = $("#missingTechniqueSelect :selected").val();
    if(image_clicked) {
      restRequest('POST', {'index':'image_positive', 'sentence_id': sentence_id, 'attack_uid':uid}, savedAlert);
      imageContext(sentence_id, uid)
    } else {
      restRequest('POST', {'index':'true_positive', 'sentence_id': sentence_id, 'attack_uid':uid}, savedAlert);
      sentenceContext(sentence_id, uid)
    }
}

