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