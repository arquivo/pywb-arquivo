sideMenuVersion = false;
printLoading = false;

function minimizeMaximize(){
	if($('#hbarMinimized').css('display') == 'none'){
	    /*The bar is Expanded - Let's minimize the bar*/
	    $('#hbar').css('display','none');
	    $('#hbarMinimized').css('display','inline-block');
	    /*Hide the Left Side Menu*/
	    $('#sidebar-wrapper').css('display','none');

	    $("#page-content-wrapper").css("cssText", "width: 100% !important;");
	    $("#page-content-wrapper").css("cssText", "left: 0% !important;");


	    /*resize vertically*/
	    resize();
	}    
	else{ 
	    /*The bar is Minimized - Let's expand the bar*/
	    $('#hbarMinimized').css('display','none');  
	    $('#hbar').css('display','inherit');
	    /*resize vertically*/
	    resize();            
	             
	}
}

function setLang(lang) {
    hostwithHttp = "{{ wbrequest.user_metadata.search_location }}";
    var cHost = hostwithHttp.substring(7);
    if(lang == 'EN')
     {
        Cookies.set('language', 'EN', { expires: 30, path: '/', domain: cHost  });
        window.location.reload();
     }
    else //default language Portuguese
    {
        Cookies.set('language', 'PT', { expires: 30, path: '/', domain: cHost  });   
        window.location.reload();
    }   
}

function createVersion(timestamp, url)
//add version with timestamp to the left side menu
{
    if (timestamp.length < 14) {
      console.log("Invalid Timestamp: " + timestamp);
    }
    else{
            var year = timestamp.substring(0, 4);
            var month = timestamp.substring(4, 6);
            var day = timestamp.substring(6, 8);
            if(day.substring(0,1) == '0')
                day = day[1]; //remove the 0 in the day just for presentation purposes
            var hours = timestamp.substring(8, 10);
            var minutes = timestamp.substring(10, 12);

        if ($('#'+year).length){
            //year already exists 
            if($('#'+year+'_'+month).length){
                
                if($('#'+year+'_'+month+'_'+day).length){
                //if day, month and year already exist  
                                  $('#'+'ul_'+year+'_'+month+'_'+day).append(   
                                            '<li style="list-style: none;" id = "'+timestamp+'">'
                                  +                         ''
                                  +                             '<a onClick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'Change Version\', \''+url+' '+timestamp+'\'); jumpToVersion(\''+url+'\', \''+timestamp+'\'); return false" href="" title="'+day+' '+Content.months[month] + ', ' + year +'" id = "a_'+timestamp+'">'+hours+':'+minutes+'</a>'
                                  +                         ''
                                  +                 '</li>');                       
                }
                else{
                //if the month and year already exist
                                  $('#'+'ul_'+year+'_'+month).append(
                                                   '<li style="list-style: none;"><a id ="'+year+'_'+month+'_'+day+'" href="#">'+day+'</a>'
                                  +                     '<ul id = "ul_'+year+'_'+month+'_'+day+'" style="list-style: none; padding: 0; margin: 0; display: none;" class="hours">'
                                  +                         '<li style="list-style: none;" id = "'+timestamp+'">'
                                  +                         ''
                                  +                             '<a onClick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'Change Version\', \''+url+' '+timestamp+'\');jumpToVersion(\''+url+'\', \''+timestamp+'\'); return false" href="/wayback/'+timestamp+'/'+url+'" title="'+day+' '+Content.months[month] + ', ' + year +'" id = "a_'+timestamp+'">'+hours+':'+minutes+'</a>'
                                  +                         '</li>'
                                  +                     '</ul>'
                                  +                 '</li>');               

                }

            }
            else{
                //year already exists, add the month 
                $('#'+'ul_'+year).append(
                                            '<li style="list-style: none;"><a id ="'+year+'_'+month+'" href="#">'+Content.months[month]+'</a>'
                                  +             '<ul id = "ul_'+year+'_'+month+'"  style="list-style: none; margin: 0; display: none;" class="days">'
                                  +                 '<li style="list-style: none;"><a id ="'+year+'_'+month+'_'+day+'" href="#" >'+day+'</a>'
                                  +                     '<ul id = "ul_'+year+'_'+month+'_'+day+'"  style="list-style: none; padding: 0; margin: 0; display: none;" class="hours">'
                                  +                         '<li style="list-style: none;" id = "'+timestamp+'">'
                                  +                         ''
                                  +                             '<a onClick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'Change Version\', \''+url+' '+timestamp+'\');jumpToVersion(\''+url+'\', \''+timestamp+'\'); return false" href="/wayback/'+timestamp+'/'+url+'" title="'+day+' '+Content.months[month] + ', ' + year +'" id = "a_'+timestamp+'">'+hours+':'+minutes+'</a>'
                                  +                         '</li>'
                                  +                     '</ul>'
                                  +                 '</li>'
                                  +             '</ul>'
                                  +         '</li>');               

            }
        }       
        
        else{   
            $("#yearList").append(
                                    '<li id="toplist">'
                                  +     '<a href="#" id = "'+year+'">' + year +'</a>'
                                  +     '<ul id ="ul_'+year+'" style="list-style: none; display: none;" class="months" >'
                                  +         '<li style="list-style: none;"><a id ="'+year+'_'+month+'" href="#" >'+Content.months[month]+'</a>'
                                  +             '<ul id = "ul_'+year+'_'+month+'"  style="list-style: none; margin: 0; display: none;" class="days">'
                                  +                 '<li style="list-style: none;"><a id ="'+year+'_'+month+'_'+day+'" href="#" >'+day+'</a>'
                                  +                     '<ul id = "ul_'+year+'_'+month+'_'+day+'"  style="list-style: none; padding: 0; margin: 0; display: none;" class="hours">'
                                  +                         '<li style="list-style: none;" id = "'+timestamp+'">'
                                  +                         ''
                                  +                             '<a onClick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'Change Version\', \''+url+' '+timestamp+'\');jumpToVersion(\''+url+'\', \''+timestamp+'\')" href="/wayback/'+timestamp+'/'+url+'" title="'+day+' '+Content.months[month] + ', ' + year +'" id = "a_'+timestamp+'">'+hours+':'+minutes+'</a>'
                                  +                         '</li>'
                                  +                     '</ul>'
                                  +                 '</li>'
                                  +             '</ul>'
                                  +         '</li>'
                                  +    '</ul>'
                                  + '</li>');
            $("#toplist").css('list-style','none');


        }


    }

    if(ts == timestamp){  //leave the current version open in the side menu

        $('#'+year).addClass('active');
        $('#'+year+'_'+month).addClass('active');
        $('#'+year+'_'+month+'_'+day).addClass('active');
        $('#a_'+timestamp).addClass('active-day');

        $('#ul_'+year).addClass('open');
        $('#ul_'+year+'_'+month).addClass('open');
        $('#ul_'+year+'_'+month+'_'+day).addClass('open');


        $('#ul_'+year).css('list-style','none'); $('#ul_'+year).css('display','block');
        $('#ul_'+year+'_'+month).css('list-style','none'); $('#ul_'+year+'_'+month).css('display','block');
        $('#ul_'+year+'_'+month+'_'+day).css('list-style','none'); $('#ul_'+year+'_'+month+'_'+day).css('display','block');
        $('#a_'+timestamp).css('font-weight','bold');

    }
        
}

/*Logging for the modal to confirm download of screenshot*/
$(document).on('opening', '.remodal', function () {
  console.log('opening');
});

$(document).on('opened', '.remodal', function () {
  console.log('opened');
});

$(document).on('closing', '.remodal', function (e) {
  console.log('closing' + (e.reason ? ', reason: ' + e.reason : ''));
});

$(document).on('closed', '.remodal', function (e) {
  console.log('closed' + (e.reason ? ', reason: ' + e.reason : ''));
});

$(document).on('confirmation', '.remodal', function () {
  console.log('confirmation');
});

$(document).on('cancellation', '.remodal', function () {
  console.log('cancellation');
});

function jumpToVersion (url, currentTs){  
  var frameSrc = wbinfo.prefix + currentTs + 'mp_/' + url;

  $('#a_'+ts).css('font-weight', 'normal') //remove the italic from the previous version
  $('#a_'+ts).removeClass('active-day'); // remove the Selected Day CSS class

  var year = ts.substring(0, 4);
  var month = ts.substring(4, 6);
  var day = ts.substring(6, 8);

  if(day.charAt(0) == '0'){
    day = day.charAt(1);
  }

  $('#'+year).removeClass('active');
  $('#'+year+'_'+month).removeClass('active');
  $('#'+year+'_'+month+'_'+day).removeClass('active');


  ts = currentTs; //update current Timestamp

  year = ts.substring(0, 4);
  month = ts.substring(4, 6);
  day = ts.substring(6, 8);

  if(day.charAt(0) == '0'){
    day = day.charAt(1);
  }

  $('#a_'+ts).css('font-weight','bold'); //italic the new selected timestamp
  $('#a_'+ts).addClass('active-day'); // add the Selected Day CSS class

  $('#'+year).addClass('active');
  $('#'+year+'_'+month).addClass('active');
  $('#'+year+'_'+month+'_'+day).addClass('active');


  $('#replay_iframe').attr('src', frameSrc); //update the iframe to the new version

  sideMenuVersion = true; // TODO:: improve this Dirty hack global var to define a leftMenu version and preserve leftMenu state
}  

function updateVersionsOfUrl(cleanurl){
  /* Uses jquery to make an ajax get request to the Cdx-server api in order to retrieve the list of versions for a specific url */
  var urlsource = cleanurl;
  var timestamp1;
  var url1;

  var requestURL = wbinfo.prefix+"-cdx"
  var tryCount = 0;
  var retryLimit = 3;

  var fromYear = ts.substring(0,4) -1 ;
  var fromTs = fromYear.toString() + ts.substring(4, ts.length);

  var toYear = ts.substring(0,4) + 1;
  var toTs = toYear.toString() + toYear.substring(4, ts.length);


  $.ajax({
  // example request to the cdx-server api - 'http://arquivo.pt/pywb/replay-cdx?url=http://www.sapo.pt/index.html&output=json&fl=url,timestamp'
     url: requestURL,
     data: {
        output: 'json',
        url: urlsource,
        fl: 'url,timestamp,status',
        filter: '!status:4|5'
     },
     error: function() {
       tryCount++;
       if (tryCount <= retryLimit) {
              $.ajax(this);
              return;
          }            
     },
     dataType: 'text',
     success: function(data) {
      $("#yearList").empty();
      $.each(data.split('\n'), function(e){
          if(this != ""){
              var version = jQuery.parseJSON(this);
              createVersion(version.timestamp, version.url); 
          } 
      }); 

     },
     type: 'GET'
  });
}

function getImageToPrint(encodedURLToPrint){
    var requestURL = wbinfo.search_location + "/print/";
    printLoading = true;
    $.ajax({
    // example request to the cdx-server api - 'http://arquivo.pt/print/?url='
       url: requestURL,
       data: {
          url: encodedURLToPrint
       },
       error: function() {
         top.alert('error printing');
       },
       dataType: 'text',
       success: function(data) {
            var theImage = jQuery.parseJSON(data);
            
            $('#divPrintMe').show();
            if($('#imgToPrint').length){ //if 2nd time user prints only update the image
                $('#imgToPrint').attr('src','data:image/png;base64,'+theImage.imgBase64);
            }
            else{
                $('#divPrintMe').append('<img id="imgToPrint" style="display: block;" width=600px src="data:image/png;base64,'+ theImage.imgBase64 + '"/>');                    
            }
            window.print();
            $('#divPrintMe').hide();

       },
       type: 'GET'
    });
}

function getDatets(){
              var year = ts.substring(0, 4);
              var month = ts.substring(4, 6);
              var day = ts.substring(6, 8);
              if(day.charAt(0) == '0'){
                day = day.charAt(1);
              }

  return day+" "+ Content.months[month]+", "+year
}

function getHoursMinutes(){
    var hours= ts.substring(8,10);
    var minutes= ts.substring(10,12);
    return hours+":"+minutes
}

/*Truncates large URL in the replay bar*/
function truncateUrl(url)
{   /*remove https and http*/
    if(url.substring(0, "https://".length) === "https://"){
      url = url.substring(8,url.length);
    }else if (url.substring(0, "http://".length) === "http://"){
      url = url.substring(7,url.length);
    }       
    if (url.length > 40){
            var newUrl = url.substring(0, 26) + "..."+ url.substring((url.length - 11),url.length);
            return newUrl;
    }
    else
        return url
}

function resize() {
  var expanded=false;
  if($('#hbarMinimized').css('display') == 'none')
      expanded=true; /*The bar is Expanded*/ 

  if(window.innerWidth >= 1024){
    if(expanded){
        $('#sidebar-wrapper').css("height", (window.innerHeight - $('#toolBar').height())  +"px");
        $('#iframeBox').css("height", (window.innerHeight - $('#toolBar').height())  +"px");
        $('#iframeBox').css("width", (window.innerWidth*.84)  +"px");
        $('#sidebar-wrapper').css('display','inherit');
        $("#page-content-wrapper").css("cssText", "width: 84% !important;");
        $("#page-content-wrapper").css("cssText", "left: 16% !important;");

    }
    else{ /*The bar is minimized*/
        $('#iframeBox').css("height", (window.innerHeight - $('#hbarMinimized').height())  +"px");
        $('#iframeBox').css("width", (window.innerWidth)  +"px");
        $('#timeMinimized').show();            
    }    
  }

  else if(window.innerWidth < 1024 && window.innerWidth > 600){
    if(expanded){
        $('#sidebar-wrapper').css("height", (window.innerHeight - $('#toolBar').height())  +"px");
        $('#iframeBox').css("height", (window.innerHeight - $('#toolBar').height())  +"px");      
        $('#iframeBox').css("width", window.innerWidth  +"px");
        $('#sidebar-wrapper').css('display','none');
        $("#page-content-wrapper").css("cssText", "width: 100% !important;");
        $("#page-content-wrapper").css("cssText", "left: 0% !important;");
    }
    else{/*The bar is minimized*/
        $('#iframeBox').css("height", (window.innerHeight - $('#hbarMinimized').height())  +"px");      
        $('#iframeBox').css("width", window.innerWidth  +"px");
        $('#timeMinimized').show();
        if(window.innerWidth < 750){ /* Hide the date if between 600 and 750*/
          $('#timeMinimized').hide();
        }  

    }                    
  }

  else if(window.innerWidth <= 600 ){
    var newPrefix = wbinfo.prefix.replace("wayback", "noFrame/replay");
    window.location.replace(newPrefix+ts+"/"+wbinfo.capture_url);
    //redirecting to the noFrame version
  }
}

$(document).ready(function() {     
    var language = Cookies.get('language');
    if (! ('ontouchstart' in document.documentElement)) {
        // if you are not in a touch device (hide scroll on the div in top of the iframe)
        $('#iframeBox').css('overflow-y','hidden');
    }

    $(document).on('click', '#yearList > li > a, #yearList > li > ul > li > a', function() {
        if ($(this).next().hasClass('open')) {
            $(this).removeClass('activeItem');
            $(this).next().slideUp('fast').removeClass('open');
            $(this).parent().css('list-style','none');                      
        } else {
            $(this).addClass('activeItem');
            $(this).next().slideDown('fast').addClass('open');
            $(this).parent().css('list-style','none');
            $(this).parent().off('hover');  
            $(this).off('hover');
        }
        return false;
    });
    
    //special case clicking on the day load the first version of that day
    $(document).on('click', '#yearList > li > ul > li > ul > li > a', function() {
        if ($(this).next().hasClass('open')) {
            $(this).removeClass('activeItem');
            $(this).next().slideUp('fast').removeClass('open');
            $(this).parent().css('list-style','none');                      
        } else {
            $(this).addClass('activeItem');
            $(this).next().slideDown('fast').addClass('open');
            $(this).parent().css('list-style','none');
            $(this).parent().off('hover');  
            $(this).off('hover');
            /*Removed span after li:first*/
            var versiontoGoTo = $(this).next().find('> li:first > a').attr("id");
            $('#'+versiontoGoTo).click();               

        }
        return false;
    });             

    var mode = 0;
    resize(); 

    window.onresize = resize;

});

$(document)
 .ajaxStart(function () {
    if(!printLoading){
      $('#tableofVersionsSpinnerLi').css('display','block');
    }
    else{                                    
      $('#a_print').hide();
      $('#printLoading').show();
    }  
 })
.ajaxStop(function () {
    if(!printLoading){
      $('#tableofVersionsSpinnerLi').css('display','none');
    }
    else{
      $('#printLoading').hide();
      $('#a_print').show();          
      printLoading="false";                                    
    }
});        