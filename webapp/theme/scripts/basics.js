var sentence_id = 0
var element_clicked_tag = "";

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

function true_positive(type, id, attack_uid, element_tag){
    $("#sentence" + id).addClass('bg-warning');
    restRequest('POST', {'index':'true_positive', 'sentence_type':type, 'sentence_id':id, 'attack_uid':attack_uid, 'element_tag':element_tag}, show_info);
    sentenceContext(id, element_tag, attack_uid)
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
    var url = document.getElementById("url").value.split(",");
    var title = document.getElementById("title").value.split(",");
    if(title.length != url.length){
      alert("Number of urls and titles do not match, please insert same number of comma seperated items.");
    }else{
      restRequest('POST', {'index':'insert_report', 'url':url, 'title':title}, show_info);
    }    
}

function upload_file(){
  //var fileName = this.val().split("\\").pop();

  console.log(document.getElementById("csv_file"))
  var file = document.getElementById("csv_file").files[0];
  if(file){
    var reader = new FileReader();
    reader.readAsText(file, "UTF-8");
    reader.onload = function(evt){
      console.log(evt.target.result)
      restRequest('POST', {'index':'insert_csv','file':evt.target.result},show_info);
    }
    reader.onerror = function(evt){
      alert("Error reading file");
    }
  }
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

function sentenceContext(data, element_tag, attack_uid){
    element_clicked_tag = element_tag
    restRequest('POST', {'index':'sentence_context', 'uid': data, 'attack_uid':attack_uid, 'element_tag':element_tag}, updateSentenceContext);
    restRequest('POST', {'index':'confirmed_sentences', 'sentence_id': data, 'element_tag':element_tag}, updateConfirmedContext);
    sentence_id = data;
}

function updateSentenceContext(data){
    $("#tableSentenceInfo tr").remove()
    $.each(data, function(index, op){
        td1 = "<td><a href=https://attack.mitre.org/techniques/" + op.attack_tid + " target=_blank>" + op.attack_technique_name + "</a></td>"
        td2 = `<td><button class='btn btn-success' onclick='true_positive(true_positive, ${op.uid}, \"${op.attack_uid}\", "${op.element_tag}")'>Accept</button></td>`
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

function downloadLayer(data){
  // Create the name of the JSON download file from the name of the report
  var json = JSON.parse(data) 
  var title = json['name'] //document.getElementById("title").value;
  var filename = title + ".json";
  // Encode data as a uri component
  var dataStr = "text/json;charset=utf-8," + encodeURIComponent(data);
  // Create temporary DOM element with attribute values needed to perform the download
  var a = document.createElement('a');
  a.href = 'data:' + dataStr;
  a.download = filename;
  a.innerHTML = 'download JSON';
  // Add the temporary element to the DOM
  var container = document.getElementById('dropdownMenu');
  container.appendChild(a);
  // Download the JSON document
  a.click();
  // Remove the temporary element from the DOM
  a.remove();
}

function viewLayer(data){
  console.info("viewLayer: " + data)
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
    restRequest('POST', {'index':'missing_technique', 'sentence_id': sentence_id, 'attack_uid':uid, 'element_tag':element_clicked_tag}, show_info);
    restRequest('POST', {'index':'confirmed_sentences', 'sentence_id': sentence_id, 'element_tag':element_clicked_tag}, updateConfirmedContext);
}

