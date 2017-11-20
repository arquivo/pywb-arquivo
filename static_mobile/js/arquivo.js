/*Arquivo.pt specific functions and js code, such as loading constants, cookies, custom html code, etc*/
var ARQUIVO = ARQUIVO || (function(){
    var _host_prefix;
    var _static_path;
	var	_url;
	var _ts;
	var _hostname = window.location.hostname;
    return {
        init : function(host_prefix, static_path) {
        	_host_prefix = host_prefix;
			_static_path = static_path;
			this.loadLanguage();
        },
        /*Choose language and load corresponding Constants*/
		loadLanguage: function(){
			var language = Cookies.get('language');
		    if( language == 'EN'){
		      $('html').attr('lang', 'en');						
		        document.write('<script type="text/javascript" language="JavaScript" src="'+_host_prefix+'/static/resources/properties/ConstantsEN.js?release=Afrodite"><\/script>');
		    }
		    else{
		      $('html').attr('lang', 'pt');
		        document.write('<script type="text/javascript" language="JavaScript" src="'+_host_prefix+'/'+_static_path+'/properties/ConstantsPT.js?release=Afrodite"><\/script>');
		    }
		},
		iframeResize: function(){ /*Code written by the author of Jquery to dynamically resize iframe to always have height equal to the parent container*/
			var buffer = 20; //scroll bar buffer
			var iframe = document.getElementById('replay_iframe');

			function pageY(elem) {
			    return elem.offsetParent ? (elem.offsetTop + pageY(elem.offsetParent)) : elem.offsetTop;
			}

			function resizeIframe() {
			    var height = document.documentElement.clientHeight;
			    height -= pageY(document.getElementById('replay_iframe'))+ buffer ;
			    height = (height < 0) ? 0 : height;
			    document.getElementById('replay_iframe').style.height = height+20 + 'px';
			}

			// .onload doesn't work with IE8 and older.
			if (iframe.attachEvent) {
			    iframe.attachEvent("onload", resizeIframe);
			} else {
			    iframe.onload=resizeIframe;
			}

			window.onresize = resizeIframe;    			
		},
		/*Write custom html code before the Iframe*/
		beforeIframe: function(){
			document.write(''+
			  '<div class="swiper-container swiper-container-horizontal noprint">'+
			  ' <div class="swiper-wrapper" id="swiperWrapper" style="">'+
			  '  <div class="swiper-slide content swiper-slide-active">'+
			  '    <div class="main-content" style="width:100%;height: 100%;">'+
			  '      <div class="container-fluid">'+
			  '        <div class="row text-center" style="padding-top:10px;padding-bottom:10px;background-color: #252525;border-bottom: solid 1px white;line-height: 30px;">'+
			  '                    <a href="/"><img src="'+_host_prefix+'/'+_static_path+'/img/01_preto.png" id="arquivoLogo" alt="Logo Arquivo.pt" style="width:auto;max-height: 30px;" class="text-center"></a>'+
			  '                    <a class="pull-right" style="color:white;font-size:23px;padding-right: 15px;line-height: 30px;vertical-align: middle; cursor: pointer;" id="menuButton"><i class="fa fa-bars" style=""></i></a>'+
			  '        </div>  '+
			  '      </div>  ');		
		},
		afterIframe: function(){
			document.write(''+
			  '   </div>' +
              '   <div class="maskMenu" style=""></div>'+
              '  </div>'+
              '		<div class="swiper-slide menu swiper-slide-prev">' +       
              '			<div style="background-color:#42a5f5">'+
			  '	 			<h4 id="menuUrl" style="padding-left: 20px; color: white;padding-bottom:0px; font-weight:bold;margin-top:0px;padding-top:10px;word-wrap: break-word;" title="'+_url+'">'+ this.truncateEndURL(_url, 20)+'</h4>' +
			  ' 			<h5 id="menuTs" style="font-weight: bold ;color: white;border-top:0px;padding-top:0px;padding-left: 20px; margin-bottom:0px; padding-bottom:10px;">'+ this.getShortDatets() +'</h5>' + 			                             
			  '			</div>'+
              ' 		<a href="http://'+_hostname+'/index.jsp?l='+Content.language+'" onclick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'NewSearchClick\', \'http://arquivo.pt/'+_ts+'/'+_url+'\');"><h4><i class="fa fa-search" aria-hidden="true"></i> '+Content.newSearch+'</h4></a>' +
              ' 		<a href="http://'+_hostname+'/search.jsp?l='+Content.language+'&query='+_url+'" onclick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'ListVersionsClick\', \'http://arquivo.pt/'+_ts+'/'+_url+'\');"><h4><i class="fa fa-list" aria-hidden="true"></i> '+Content.allVersions+'</h4></a>' +
              ' 		<a href="#" id="shareMenu"><h4><i class="fa fa-share-alt" aria-hidden="true"></i> '+Content.share+'<i id="shareCarret" class="fa fa-caret-down iCarret shareCarret pull-right" aria-hidden="true"></i></h4></a>'+
              '			<div id="shareOptions">'+
              ' 			<a class="addthis_button_facebook" onclick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'FacebookShareClick\', \'http://arquivo.pt/'+_ts+'/'+_url+'\');" href=""><h4 class="submenu"><i class="fa fa-facebook" aria-hidden="true"></i> '+ Content.facebook+'</h4></a>'+
              ' 			<a class="addthis_button_twitter" onclick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'TwitterShareClick\', \'http://arquivo.pt/'+_ts+'/'+_url+'\');" ><h4 class="submenu"><i class="fa fa-twitter" aria-hidden="true"></i> '+Content.twitter+'</h4></a>'+
              ' 			<a title="'+Content.mailTitle+'" href="mailto:?subject='+Content.emailMessage+'[sub]" onclick="this.href = this.href.replace(\'[sub]\',document.title + \'%0D%0A'+ encodeURIComponent(this.getDatets()) +'%0D%0A %0D%0A\' + encodeURIComponent(window.location.href) ); ga(\'send\', \'event\', \'ReplayBarFunctions\', \'EmailShareClick\', \'http://arquivo.pt/'+_ts+'/'+_url+'\');""><h4 class="submenu"><i class="fa fa-envelope" aria-hidden="true"></i> '+Content.email+'</h4></a>'+
			  '			</div>'+
              ' 		<a href="#" id="toolsMenu"><h4><i class="fa fa-cogs" aria-hidden="true"></i> '+Content.tools+'<i id="toolsCarret" class="fa fa-caret-down iCarret shareCarret pull-right" aria-hidden="true"></i></h4></a>'+
              '			<div id="toolsOptions">'+
              '	 			<a id="completePage"><h4 class="submenu"><i class="fa fa-plus-circle" aria-hidden="true"></i> '+Content.complete+'</h4></a>' +
              ' 			<a id="screenshotOption"><h4 class="submenu"><i class="fa fa-camera" aria-hidden="true"></i> '+Content.saveImage+'</h4></a>' +
              ' 			<a id="printOption"><h4 class="submenu"><i class="fa fa-print" aria-hidden="true"></i> '+Content.print+'</h4></a>'+
              '			</div>'+
              '		 <a href="'+Content.helpHref+'" onclick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'HelpClick\', \'http://arquivo.pt/'+_ts+'/'+_url+'\');"><h4><i class="fa fa-question-circle" aria-hidden="true"></i> '+Content.help+'</h4></a>'+
              '		 <a id="changeLanguage" onclick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'ChangeLanguageTo'+Content.otherLanguage+'Click\', \'http://arquivo.pt/'+_ts+'/'+_url+'\');"><h4><i class="fa fa-flag" aria-hidden="true"></i> '+Content.otherLanguageExtended+'</h4></a>'+
              '		</div>'+
              '	</div>'+
			  '</div>'+
			  '<div id="divPrintMe"></div>');
			this.attachScreenshotModal();
			this.attachPrintModal();
			this.attachCompletePageModal();
			this.iframeResize();
			this.createSlideMenu();
			this.attachLanguageChange();
			this.attachShare();
			this.attachTools();
 		},
 		updateInfo: function(url, ts){
 			_url = url;
 			_ts = ts;
			/*get new page title and update it*/  
			var title = $("#replay_iframe").contents().find("meta[property='og:title']").attr("content");
			if(title === undefined || title === null) // there is no og:title meta tag in this iframe
			{
			  title = $("#replay_iframe").contents().find("title").html(); //search for a title tag in the iframe
			  if (title === undefined || !title.length){ //there is no title 
			      //top.alert("No title");
			      title = "Arquivo.pt"/*Content.shareMessage;*/
			  }
			}
			title = title + " - preservado pelo Arquivo.pt"/*Content.preservedByArquivo*/;
			document.title = title;

			var addthis_config = addthis_config||{};
			addthis_config.data_track_addressbar = false;
			addthis_config.data_track_clickback = false;

			theurl= 'http://arquivo.pt/wayback/'+_ts+'/'+_url;
			/*addthis.update('share', 'url', theurl);
			addthis.update('share', 'title', title);
			addthis.toolbox('.addthis_toolbox', addthis_config, addthis_share); */

			$('#menuUrl').attr('title', _url);
			$('#menuUrl').html(ARQUIVO.truncateEndURL(_url,20)); /*update menu url*/
			$('#menuTs').html(ARQUIVO.getShortDatets()); /*update menu ts*/

			ga('send', 'pageview'); /*New page*/ 			
 		},
 		createSlideMenu: function(){
		    var ignoreInitialTransitionEnd = 0;
		    var toggleMenu = function(){
		      if (swiper.previousIndex == 0)
		        swiper.slidePrev()
		    }
		    /*, menuButton = document.getElementsByClassName('menu-button')[0]*/
		    , swiper = new Swiper('.swiper-container', {
		      slidesPerView: 'auto'
		      , initialSlide: 1
		      , resistanceRatio: .00000000000001
		      , onSlideChangeStart: function(slider) {
		        if (slider.activeIndex == 0) {
		          /*menuButton.removeEventListener('click', toggleMenu, false)*/
		        }
		          
		      }

		      ,onTransitionEnd: function(slider){
		        if(ignoreInitialTransitionEnd === 0){
		          ignoreInitialTransitionEnd+=1;
		          return;
		        }
		        if( $('.swiper-wrapper').css('transform').split(',')[4] != 0){
		          $('.swiper-wrapper').addClass('active');
		          $('.maskMenu').fadeIn(150);    
		        }
		        else{
		          $('.swiper-wrapper').removeClass('active');
		          $('.maskMenu').fadeOut();             
		        }
		      }
		      , onSlideChangeEnd: function(slider) {
		        if (slider.activeIndex == 0){
		          menuButton.removeEventListener('click', toggleMenu, false);
		        }
		        else{
		          $('.swiper-wrapper').addClass('active');
		          menuButton.addEventListener('click', toggleMenu, false);
		        }
		      }
		      , slideToClickedSlide: true
		    })
	        $('.swiper-wrapper').css('-webkit-transition', 'all 0s linear' );
	        $('.swiper-wrapper').css('-moz-transition', 'all 0s linear' );
	        $('.swiper-wrapper').css('-o-transition', 'all 0s linear' );
	        $('.swiper-wrapper').css('-ms-transition', 'all 0s linear' );
	        $('.swiper-wrapper').css('transition', 'all 0s linear' );
	        $('.swiper-wrapper').css('transform', 'translate3d(0px, 0px, 0px)' );
	        $('.swiper-wrapper').css('-webkit-transform', 'translate3d(0px, 0px, 0px)' );	
			$('.maskMenu').on('click', function (e) { 
				ARQUIVO.closeSwipeMenu(); 
			});  
			$('#menuButton').on('click', function(e){
				ga('send', 'event', 'ReplayBarFunctions', 'MainMenuClick', 'http://arquivo.pt/'+_ts+'/'+_url);
				$('.swiper-wrapper').addClass('active');
				$('.swiper-wrapper').css('-webkit-transition', 'all 0.3s linear' );
				$('.swiper-wrapper').css('-moz-transition', 'all 0.3s linear' );
				$('.swiper-wrapper').css('-o-transition', 'all 0.3s linear' );
				$('.swiper-wrapper').css('-ms-transition', 'all 0.3s linear' );
				$('.swiper-wrapper').css('transition', 'all 0.3s linear' );
				$('.swiper-wrapper').css('transform', 'translate3d(-'+$('.menu').width()+'px, 0px, 0px)' );
				$('.swiper-wrapper').css('-webkit-transform', 'translate3d(-'+$('.menu').width()+'px, 0px, 0px)' );
				$('.maskMenu').fadeIn(150);    
			});	        	    
 		},
 		attachScreenshotModal: function(){
		  $('#screenshotOption').on('click', function(e){
		  	ARQUIVO.closeSwipeMenu();    		  	
		  	ARQUIVO.screenshotModal();		  	
		  }); 			
 		}, 		
 		/*When user clicks on the screenshot link generate screenshot of current url*/
 		attachScreenshot: function(){
		  $('#takeScreenshot').on('click', function(e){
		  	ARQUIVO.closeUglipop();
		    window.open('http://'+_hostname+'/screenshot/?url='+encodeURIComponent("http://"+_hostname+"/noFrame/replay/"+ _ts+'/'+_url)+"&width="+window.screen.width/*window.innerWidth*/+"&height="+/*window.innerHeight*/ window.screen.height);
		  }); 			
 		},
 		attachPrintModal: function(){
		  $('#printOption').on('click', function(e){
		  	ARQUIVO.closeSwipeMenu();    		  	
		  	ARQUIVO.printModal();
		  }); 			
 		}, 
 		attachPrint: function(){
		  $('#printPage').on('click', function(e){
		    ARQUIVO.getImageToPrint("http://"+_hostname+"/noFrame/replay/"+ _ts+"/"+_url);
		  }); 			
 		}, 
 		attachCompletePageModal: function(){
		  $('#completePage').on('click', function(e){
		  	ARQUIVO.closeSwipeMenu();    		  	
		  	ARQUIVO.completePageModal();		  	
		  }); 			
 		}, 		 		 				
 		attachShare: function(){
		  $('#shareMenu').on('click', function(e){
		  	ga('send', 'event', 'ReplayBarFunctions', 'ShareMenuClick', 'http://arquivo.pt/'+_ts+'/'+_url);
		    $('#shareCarret').toggleClass('fa-caret-up fa-caret-down');
		    $('#shareOptions').slideToggle( "fast", "linear" );
		  }); 	 			
 		}, 	
 		attachTools: function(){
		  $('#toolsMenu').on('click', function(e){
		  	ga('send', 'event', 'ReplayBarFunctions', 'ToolsMenuClick', 'http://arquivo.pt/'+_ts+'/'+_url);		  	
		    $('#toolsCarret').toggleClass('fa-caret-up fa-caret-down');
		    $('#toolsOptions').slideToggle( "fast", "linear" );
		  }); 	 			
 		}, 	 			

 		attachLanguageChange: function(){
		  $('#changeLanguage').on('click', function(e){
		    ARQUIVO.setLang(Content.otherLanguage);
		  }); 	 			
 		},
 		/*Choose language*/
		setLang: function(lang) {
		    if(lang == 'EN')
		     {
		        Cookies.set('language', 'EN');
		        window.location.reload();
		     }
		    else //default language Portuguese
		    {
		        Cookies.set('language', 'PT');   
		        window.location.reload();
		    }   
		},
		truncateURL: function(url, maxLength){
			var middleLength = 8;
			if(maxLength > 5){
				middleLength = (maxLength-3)/2;
			}
			url = url.replace(/(^\w+:|^)\/\//, ''); /*remove protocol from url*/
			if(url.length > maxLength){
				url = url.substring(0,middleLength) + '...' + url.substring(url.length-middleLength, url.length);
			}
			return url;
		},
		truncateEndURL: function(url, maxLength){
			url = url.replace(/(^\w+:|^)\/\//, ''); /*remove protocol from url*/
			if(url.length > maxLength){
				url = url.substring(0, maxLength - 3) + '...' ;
			}
			return url;
		},		
		/*Returns current timestamp in short form such as '2 Nov, 2015' */
		getShortDatets: function(){
		              var year = _ts.substring(0, 4);
		              var month = _ts.substring(4, 6);
		              var day = _ts.substring(6, 8);
		              if(day.charAt(0) == '0'){
		                day = day.charAt(1);
		              }

		  return day+" "+ Content.months[month]+", "+year;
		},
		getDatets: function(){
		              var year = ts.substring(0, 4);
		              var month = ts.substring(4, 6);
		              var day = ts.substring(6, 8);
		              if(day.charAt(0) == '0'){
		                day = day.charAt(1);
		              }
		  return day+" "+ Content.months[month]+", "+year;
		},
		getImageToPrint: function(encodedURLToPrint){
			ARQUIVO.closeUglipop();
			ARQUIVO.loadingModal();
		    var requestURL = "http://"+_hostname+ "/print";
		    $.ajax({
		    // example request to the cdx-server api - 'http://arquivo.pt/print/?url='
		       url: requestURL,
		       data: {
		          url: encodedURLToPrint
		       },
		       dataType: 'text',
   		       error: function() {
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
		       	ARQUIVO.loadingModal();
        		console.log(this.url);
    		   },
		       type: 'GET',
		    });
		},
		printModal: function(){
			ga('send', 'event', 'ReplayBarFunctions', 'PrintMenuClick', 'http://arquivo.pt/'+_ts+'/'+_url);
		    uglipop({
		      class:'modalReplay noprint', //styling class for Modal
		      source:'html',
		      content:'<h4 class="modalTitle"><i class="fa fa-print" aria-hidden="true"></i> '+Content.printModalTitle+'</h4>'+
		              '<div class="row"><a id="printPage" onclick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'PrintMenuConfirm\', \'http://arquivo.pt/'+_ts+'/'+_url+'\');" class="col-xs-6 text-center leftAnchor modalOptions">Ok</a><a id="cancelPopup" onclick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'PrintMenuCancel\', \'http://arquivo.pt/'+_ts+'/'+_url+'\');" class="col-xs-6 text-center modalOptions">'+Content.cancel+'</a></div>'});
		    this.attachPrint();          			
		    this.attachClosePopup();
		},
		screenshotModal: function(){
			ga('send', 'event', 'ReplayBarFunctions', 'ScreenshotMenuClick', 'http://arquivo.pt/'+_ts+'/'+_url);			
		    uglipop({
		      class:'modalReplay noprint', //styling class for Modal
		      source:'html',
		      content:'<h4 class="modalTitle"><i class="fa fa-camera" aria-hidden="true"></i> '+Content.saveAsImage+'</h4>'+
		              '<div class="row"><a id="takeScreenshot" onclick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'ScreenshotMenuConfirm\', \'http://arquivo.pt/'+_ts+'/'+_url+'\');" class="col-xs-6 text-center leftAnchor modalOptions">Ok</a><a id="cancelPopup" onclick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'ScreenshotMenuCancel\', \'http://arquivo.pt/'+_ts+'/'+_url+'\');" class="col-xs-6 text-center modalOptions">'+Content.cancel+'</a></div>'});
		    this.attachScreenshot();          			
		    this.attachClosePopup();
		},
		completePageModal: function(){
			ga('send', 'event', 'ReplayBarFunctions', 'CompletePageMenuClick', 'http://arquivo.pt/'+_ts+'/'+_url);						
		    uglipop({
		      class:'modalReplay noprint', //styling class for Modal
		      source:'html',
		      content:'<h4 class="modalTitleComplete"><i class="fa fa-plus-circle" aria-hidden="true"></i> '+Content.completeThisPage+'</h4>'+
		              '<p class="modalparagraph first">'+Content.leavingArquivo+'</p>'+
		      		  '<p class="modalparagraph last">'+Content.toBeCompleted+'</p>'+
		              '<div class="row"><a id="completePageOption" onclick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'CompletePageConfirm\', \'http://arquivo.pt/'+_ts+'/'+_url+'\');" href="http://timetravel.mementoweb.org/reconstruct/'+_ts+'/'+_url+'" class="col-xs-6 text-center leftAnchor modalOptions">Ok</a><a id="cancelPopup" onclick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'CompletePageCancel\', \'http://arquivo.pt/'+_ts+'/'+_url+'\');" class="col-xs-6 text-center modalOptions">'+Content.cancel+'</a></div>'});       			
		    this.attachClosePopup();
		},

		loadingModal: function(){
			$('.maskMenu').toggle();
			$('#loadingAnimation').toggle();
		},		
		closeUglipop: function(){
			$('#uglipop_content_fixed').fadeOut();
			$('#uglipop_overlay').fadeOut('fast');
		},
 		attachClosePopup: function(){
		  $('#cancelPopup').on('click', function(e){
		  	ARQUIVO.closeUglipop();
		  }); 	 			
 		},
		closeSwipeMenu: function(){
	      $('.swiper-wrapper').css('-webkit-transition', 'all 0.3s linear' );
	      $('.swiper-wrapper').css('-moz-transition', 'all 0.3s linear' );
	      $('.swiper-wrapper').css('-o-transition', 'all 0.3s linear' );
	      $('.swiper-wrapper').css('-ms-transition', 'all 0.3s linear' );
	      $('.swiper-wrapper').css('transition', 'all 0.3s linear' );
	      $('.swiper-wrapper').css('transform', 'translate3d(0px, 0px, 0px)' );
	      $('.swiper-wrapper').css('-webkit-transform', 'translate3d(0px, 0px, 0px)' );
	      $('.swiper-wrapper').removeClass('active');
	      $('.maskMenu').fadeOut(); 
		} 		 									 		
    };
}());

