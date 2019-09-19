String.prototype.replaceAll = String.prototype.replaceAll || function(needle, replacement) {
    return this.split(needle).join(replacement);
}; 

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
                                  +                             '<a onClick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'Change Version\', \''+url+' '+timestamp+'\');jumpToVersion(\''+url+'\', \''+timestamp+'\'); return false" href="/'+timestamp+'/'+url+'" title="'+day+' '+Content.months[month] + ', ' + year +'" id = "a_'+timestamp+'">'+hours+':'+minutes+'</a>'
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
                                  +                             '<a onClick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'Change Version\', \''+url+' '+timestamp+'\');jumpToVersion(\''+url+'\', \''+timestamp+'\'); return false" href="/'+timestamp+'/'+url+'" title="'+day+' '+Content.months[month] + ', ' + year +'" id = "a_'+timestamp+'">'+hours+':'+minutes+'</a>'
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
                                  +                             '<a onClick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'Change Version\', \''+url+' '+timestamp+'\');jumpToVersion(\''+url+'\', \''+timestamp+'\')" href="/'+timestamp+'/'+url+'" title="'+day+' '+Content.months[month] + ', ' + year +'" id = "a_'+timestamp+'">'+hours+':'+minutes+'</a>'
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

function attachMoreInfoModal(){
       $('#a_moreinfo').on('click', function(e){         
        moreInfoModal();        
      });    
}

function moreInfoModal(){
  ga('send', 'event', 'ReplayBarFunctions', 'MoreInformationMenuClick', 'arquivo.pt/'+ts+'/'+url);
    var requestURL = "//"+window.location.hostname+ "/textsearch";
    metadataResponse= '';
      $.ajax({
      // example request to the cdx-server api - 'http://arquivo.pt/textsearch?metadata=http%3A%2F%2Fquiz.musicbox.sapo.pt%2F%2F20131108093638'
          url: requestURL,
          data: {
            metadata: url+"/"+ts
          },
          dataType: 'text',

        error: function() {
             printLoading= false; 
             console.log('error showing metadata');
         },
         success: function(data) {
              var theMetadata = jQuery.parseJSON(data).response_items;
              for(var obj in theMetadata){
                  if(theMetadata.hasOwnProperty(obj)){
                    for(var prop in theMetadata[obj]){
                        if(theMetadata[obj][prop] === '') continue; /*do not show empty fields*/
                        if(theMetadata[obj].hasOwnProperty(prop)){
                          if(theMetadata[obj][prop].startsWith('http')){
                            metadataResponse += '<p class="modalparagraph"><strong>'+prop + '</strong>: <a target=_blank href="'+theMetadata[obj][prop]+'">' + theMetadata[obj][prop] + '</a></p>';    
                          }
                          else if(prop == "collection"){
                            metadataResponse += '<p class="modalparagraph"><strong>'+prop + '</strong>: <a target=_blank href="https://archive.org/details/portuguese-web-archive?sin=&and[]='+ theMetadata[obj][prop] +'&and[]=subject%3A%22pwacrawlid%3A'+ theMetadata[obj][prop] +'%22&and[]=collection%3A%22portuguese-web-archive%22">' + theMetadata[obj][prop] + '</a></p>';
                          }
                          else{
                           metadataResponse += '<p class="modalparagraph"><strong>'+prop + '</strong>: ' + theMetadata[obj][prop] + '</p>';
                          }
                        }
                    }
                  }
              }            
              console.log('Success: '+ metadataResponse);

              uglipop({
                class:'modalReplay noprint scrollModal', //styling class for Modal
                source:'html',
                content:'<button id="removeModal" class="expand__close" title="Fechar"></button>'+
                        '<h4 class="modalTitle"><i  alt="'+Content.moreInfoIcon+'" class="ion ion-information-circled menu-icon"></i> '+Content.moreInfoIcon+' <a target="_blank" href="https://github.com/arquivo/pwa-technologies/wiki/Arquivo.pt-API-v.0.2-(beta-version)#response-fields">'+Content.techDetails+'</a></h4>'+
                        '<div>' + metadataResponse + '</div>'
              });
              attachRemoveModal();
              $( ".scrollModal" ).ready(function() {
                $( ".scrollModal" ).parent().css({
                    'top': '10px',
                    'left': '10%',
                    'bottom': '10px',
                    'width': '80%',
                    'height': '80%', 
                    'opacity': '0.9',  
                    'overflow': 'auto' ,
                    'transform': 'none',
                    '-webkit-transform': 'none',
                    '-ms-transform': 'unset'
                });

              }); 
              loadedModal = true;
         },
         type: 'GET',
      });   
}


function attachRemoveModal(){
       $('#removeModal').on('click', function(e){    
          closeUglipopCustomCss();  
        });
       $('#uglipop_overlay').on('click', function(e){
          if( $('#uglipop_popbox').hasClass('scrollModal')){
            closeUglipopCustomCss();
          }
       });    
}

function screenshotModal(){
  ga('send', 'event', 'ReplayBarFunctions', 'ScreenshotMenuClick', 'arquivo.pt/'+ts+'/'+url);      
  uglipop({
    class:'modalReplay noprint', //styling class for Modal
    source:'html',
    content:'<h4 class="modalTitle"><i class="fa fa-camera" aria-hidden="true"></i> '+Content.saveAsImage+'</h4>'+
            '<div class="row"><a id="takeScreenshot" onclick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'ScreenshotMenuConfirm\', \'arquivo.pt/'+ts+'/'+url+'\');" class="col-xs-6 text-center leftAnchor modalOptions">OK</a><a id="cancelPopup" onclick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'ScreenshotMenuCancel\', \'arquivo.pt/'+ts+'/'+url+'\');" class="col-xs-6 text-center modalOptions">'+Content.cancel+'</a></div>'});
  attachScreenshot();                
  attachClosePopup();
}


function attachScreenshotModal(){
      $('#a_screenshot').on('click', function(e){         
        screenshotModal();        
      });       
}
/*When user clicks on the screenshot link generate screenshot of current url*/
function attachScreenshot() {
  $('#takeScreenshot').on('click', function(e){
    closeUglipop();
    window.open('//'+window.location.hostname+'/screenshot/?url='+encodeURIComponent(window.location.protocol+"//"+window.location.hostname+"/noFrame/replay/"+ ts+'/'+url)+"&width="+window.screen.width/*window.innerWidth*/+"&height="+/*window.innerHeight*/ window.screen.height);
  });       
}

function attachCompletePageModal(){
      $('#a_reconstruct').on('click', function(e){         
        completePageModal();        
      });       
}

function attachSwitchMobile(){
  $('#switchMobile').on('click', function(e){         
      Cookies.set('forceDesktop', 'false', { domain: window.location.hostname});
      window.location =   window.location.href.replace(window.location.hostname, "m."+window.location.hostname);       
  });       
}

function attachClosePopup(){
  $('#cancelPopup').on('click', function(e){
    closeUglipop();
  });         
}

function closeUglipop(){
  $('#uglipop_content_fixed').fadeOut();
  $('#uglipop_overlay').fadeOut('fast');
}

function closeUglipopCustomCss(){
  $('#uglipop_content_fixed').hide();
  $('#uglipop_overlay').hide();
  $( "#uglipop_content_fixed" ).css({
                  'top': '50%',
                  'left': '50%',
                  'bottom': '',
                  'width': '',
                  'height': '', 
                  'opacity': '1',  
                  'overflow': 'auto' ,
                  'transform': 'translate(-50%, -50%)',
                  '-webkit-transform': 'translate(-50%, -50%)',
                  '-ms-transform': 'translate(-50%, -50%)'
  });
}


function attachPrintModal(){
  $('#printOption').on('click', function(e){
    e.preventDefault();       
    printModal();
  });       
}
function completePageModal(){
  ga('send', 'event', 'ReplayBarFunctions', 'Reconstruct', 'arquivo.pt/'+ts+'/'+url);
    uglipop({
      class:'modalReplay noprint', //styling class for Modal
      source:'html',
      content:'<h4 class="modalTitleComplete"><img class="reconstruct_modal" id="reconstructImg" alt="'+Content.reconstructImg+'" src="//'+window.location.hostname+'/static/img/reconstruct.png"> '+Content.completePage+'</h4><p class="modalparagraph last">  '+Content.leavingArquivo+'</p>'+
              '<div class="row"><a id="completePage"  class="col-xs-6 text-center leftAnchor modalOptions">OK</a><a id="cancelPopup" class="col-xs-6 text-center modalOptions">'+Content.cancel+'</a></div>'});               
  attachCompletepage();
  attachClosePopup();
}

function attachCompletepage(){
    $('#completePage').on('click', function(e){
        ga('send', 'event', 'Complete Page', 'Clicked complete page and confirmed', 'arquivo.pt/'+ts+'/'+url);
        window.open('https://timetravel.mementoweb.org/reconstruct/'+ts+'/'+url);
        closeUglipop();
    });    
}

function attachReportBug(){
    $('#reportBug').click( function(e) {
        e.preventDefault();
        ga('send', 'event', 'ReplayBarFunctions', 'ReportBug', window.location.href);
        window.location = Content.bug + window.location.href.replaceAll('&', '%26');
      });
}


function printModal(){
  ga('send', 'event', 'ReplayBarFunctions', 'PrintMenuClick', 'arquivo.pt/'+ts+'/'+url);
    uglipop({
      class:'modalReplay noprint', //styling class for Modal
      source:'html',
      content:'<h4 class="modalTitle"><i class="fa fa-print" aria-hidden="true"></i> '+Content.printModalTitle+'</h4>'+
              '<div class="row"><a id="printPage" onclick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'PrintMenuConfirm\', \'https://arquivo.pt/'+ts+'/'+url+'\');" class="col-xs-6 text-center leftAnchor modalOptions">OK</a><a id="cancelPopup" onclick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'PrintMenuCancel\', \'arquivo.pt/'+ts+'/'+url+'\');" class="col-xs-6 text-center modalOptions">'+Content.cancel+'</a></div>'});
  attachPrint();               
  attachClosePopup();
}

function attachPrint(){
  $('#printPage').on('click', function(e){
    getImageToPrint("https://"+window.location.hostname+"/noFrame/replay/"+ ts+"/"+url);
  });       
}      

function getImageToPrint(encodedURLToPrint){
    closeUglipop();
    openingModal();
    printLoading= true;
    var requestURL = "//"+window.location.hostname+ "/print";
    $.ajax({
    // example request to the cdx-server api - 'http://arquivo.pt/print/?url='
       url: requestURL,
       data: {
          url: encodedURLToPrint
       },
       dataType: 'text',
         error: function() {
           printLoading= false; 
           top.alert('error printing');
           top.alert('url: ' + requestURL+'?url='+encodedURLToPrint);
       },
       success: function(data) {
            var theImage = jQuery.parseJSON(data);
            $('#divPrintMe').show();
            if($('#imgToPrint').length){ //if 2nd time user prints only update the image
                $('#imgToPrint').attr('src','data:image/png;base64,'+theImage.imgBase64);
            }
            else{
                $('#divPrintMe').append('<img id="imgToPrint" style="display: block;" width=600px src="data:image/png;base64,'+ theImage.imgBase64 + '"/>');                    
            }
            setTimeout(function(){
            window.print();
      }, 200); /*Wait 200ms for element to be created before printing*/
            setTimeout(function(){
              $('#divPrintMe').hide();
      }, 1000); /*Wait 1s for image to be printed before hiding it*/          

       },
       complete : function(){
        printLoading= false;
        closingModal();
        console.log(this.url);
       },
       type: 'GET',
    });
}

function openingModal(){
  $('.maskMenu').show();
  $('#loadingAnimation').show();
}  
function closingModal(){
  $('.maskMenu').hide();
  $('#loadingAnimation').hide();
}  


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

  var requestURL = wbinfo.prefix+"cdx"
  var tryCount = 0;
  var retryLimit = 3;

  var fromYear = ts.substring(0,4) -1 ;
  var fromTs = fromYear.toString() + ts.substring(4, ts.length);

  var toYear = ts.substring(0,4) + 1;
  var toTs = toYear.toString() + toYear.substring(4, ts.length);

  var filterErrorPages = sessionStorage.showErrorPages == "true" ? '' : '!status:4|5';


  $.ajax({
  // example request to the cdx-server api - 'http://arquivo.pt/pywb/replay-cdx?url=http://www.sapo.pt/index.html&output=json&fl=url,timestamp'
     url: requestURL,
     data: {
        output: 'json',
        url: urlsource,
        fl: 'url,timestamp,status',
        filter: filterErrorPages
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

  if(window.innerWidth >= 1280){
    if(expanded){
        console.log("desktop mode");
        $('#urlTopbarDiv').css('display', 'inline-block');
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

  else{ /*Resolution smaller than 1280 redirect to mobile version*/
    window.location = window.location.href.replace(window.location.hostname, "m."+window.location.hostname);  
  }

}

$(document).ready(function() {     
    var language = localStorage.language;
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
 })
.ajaxStop(function () {
    if(!printLoading){
      $('#tableofVersionsSpinnerLi').css('display','none');
    }
    else{       
      printLoading="false";                                    
    }
});        
