String.prototype.replaceAll = String.prototype.replaceAll || function(needle, replacement) {
    return this.split(needle).join(replacement);
}; 
/*Arquivo.pt specific functions and js code, such as loading constants, cookies, custom html code, etc*/
var ARQUIVO = ARQUIVO || (function(){
    var _host_prefix;
    var _static_path;
	var	_url;
	var _ts;
	var _hostname = window.location.hostname;
	var _language ='pt';
	var _patching = '';
    return {
        init : function(static_path) {
			_static_path = static_path;
			this.loadLanguage();
        },
        /*Choose language and load corresponding Constants*/
		loadLanguage: function(){
			var language = localStorage.language;
		    if( language == 'EN'){
		      $('html').attr('lang', 'en');						
		        document.write('<script type="text/javascript" language="JavaScript" src="'+_static_path+'/properties/ConstantsEN.js?release=Zeus"><\/script>');
		        _language = 'en';
		    }
		    else{
		      _language ='pt';	
		      $('html').attr('lang', 'pt');
		        document.write('<script type="text/javascript" language="JavaScript" src="'+_static_path+'/properties/ConstantsPT.js?release=Zeus"><\/script>');
		    }
		},
		iframeResize: function(){ /*Code written by the author of Jquery to dynamically resize iframe to always have height equal to the parent container*/
			var buffer = 20; //scroll bar buffer
			var overlayBuffer = 27 // overlay current style with a curve in the replaybar
			var iframe = document.getElementById('replay_iframe');
	

			function pageY(elem) {
			    return elem.offsetParent ? (elem.offsetTop + pageY(elem.offsetParent)) : elem.offsetTop;
			}

			function resizeIframe() {
			    var height = document.documentElement.clientHeight;
			    height -= pageY(document.getElementById('replay_iframe'))+ buffer+ overlayBuffer ;
			    height = (height < 0) ? 0 : height;
			    document.getElementById('replay_iframe').style.height = height+ buffer +overlayBuffer + 'px';
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
			  '<div id="swipeContainer" class="swiper-container swiper-container-horizontal noprint">'+
			  ' <div class="swiper-wrapper" id="swiperWrapper">'+
			  '  <div class="swiper-slide content swiper-slide-active">'+
			  '    <div class="main-content">'+
			  '      <div class="container-fluid">'+
			  '        <div class="row text-center logo-main-div-no-border">'+
			  '                    <a class="logo-menu-anchor" href="/?l='+_language+'"><img src="'+_static_path+'/img/arquivo-logo-white.svg  " id="arquivoLogo" alt="Logo Arquivo.pt" class="text-center logo-main"></a>'+
			  '                    <a class="pull-left main-menu" id="menuButton"><div class="menu-button"><div class="bar"></div><div class="bar"></div><div class="bar"></div></div></a><button  id="replayMenuButton" " class="select-language" title="Replay menu">...</button>'+
			  '        </div>  '+
			  '      </div>  '+
	'<div class="curve-background"></div>'+
	'<div class="background-top-curve"><p>&rarr; Insert here dynamically url from the page plus date - <a href="#">See all available versions</a> </p></div>');
		},
		afterIframe: function(){
			var reconstructMenu = '';
			if( _patching.toLowerCase( ) === 'true' ) {
				reconstructMenu = '			<a id="a_reconstruct" alt="'+Content.completePage+'" href=\'/noFrame/patching/record/'+_ts+'/'+_url+'\' onclick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'Complete Page\', \'arquivo.pt/'+_ts+'/'+_url+'\');"><h4><i class="complete-page"></i>'+Content.completePage+'</h4></a>';
			} else {
				reconstructMenu = '			<a id="a_reconstruct" alt="'+Content.completePage+'" href=javascript:void(0) onclick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'Complete Page\', \'arquivo.pt/'+_ts+'/'+_url+'\'); ARQUIVO.attachCompletePageModal();"><h4><i class="complete-page"></i>'+Content.completePage+'</h4></a>';
			}

			document.write(''+
			  '   </div>' +
              '   <div id="mainMask" class="maskMenu"></div>'+
              '  </div>'+
              '  <div class="swiper-slide replayMenu swiper-slide-next">'+
              '			<div class="main-menu-top-div">'+
			  '	 			<h4 id="menuUrl" title="'+_url+'">'+ _url +'</h4>' + 
			  ' 			<button href="#" onclick="ARQUIVO.goToContent()" class="close-functions clean-button-no-fill" id="closeSpecPopUp">&#10005;</button>' +			  
			  ' 			<h5 id="menuTs">'+ this.getShortDatets() +'</h5>' + 			                             
			  '			</div>'+
			  '			<a href="//'+_hostname+'/search.jsp?l='+Content.language+'&query='+encodeURIComponent(_url)+'" onclick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'ListVersionsClick\', \'arquivo.pt/'+_ts+'/'+_url+'\');"><h4><i class="fa fa-list" aria-hidden="true"></i> '+Content.allVersions+'</h4></a>'+ 						                      
			  ' 		<a href="#" id="a_moreinfo" title="'+Content.moreInfoIcon+'"><h4><i class="fa fa-info-circle right-9" aria-hidden="true"></i> '+Content.moreInfoIcon+'</h4></a>'+			  
              ' 		<a id="screenshotOption"><h4><i class="fa fa-camera right-5" aria-hidden="true"></i> '+Content.saveImage+'</h4></a>' +
			  '	 		<a id="printOption"><h4><i class="fa fa-print right-7" aria-hidden="true"></i> '+Content.print+'</h4></a>'+
			  			reconstructMenu +
			  '		 	<a id="expandPage" href="/noFrame/replay/'+_ts+'/'+_url+'" onclick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'ExpandClick\', \'arquivo.pt/'+_ts+'/'+_url+'\');"><i class="fa fa-expand" aria-hidden="true"></i><span style="padding-left: 13px !important;">'+Content.expandPage+'</span></a>'+
			  '			<a id="replayWithOldBrowsers" alt="'+Content.replayWithOldBrowsers+'" href=javascript:void(0) onclick="ARQUIVO.replayWithOldBrowsers();"><h4><i class="replay-with-old-browsers"></i>'+Content.replayWithOldBrowsers+'</h4></a>'+
              '  </div>'+
              '	</div>'+
			  '</div>'+
			  '<div id="divPrintMe"></div>');
			this.attachScreenshotModal();
			this.attachPrintModal();
			this.iframeResize();
			this.createSlideMenu();
			this.attachLanguageChange();
			this.attachShare();
			this.attachTools();
			this.attachSwitchDesktop();
			this.attachMoreInfoModal();
			this.attachReportBug();
			this.attachCompletepage();
			this.attachKeyBoardEvent();
 		},
 		goToContent: function(){
 			const mySwiper = document.querySelector('.swiper-container').swiper;
 			mySwiper.slideTo(1);
 		},
 		copyLink: function(){
			var dummy = document.createElement('input')	    
			var urlToCopy= window.location.href;

			document.body.appendChild(dummy);
			dummy.value = urlToCopy;
			dummy.select();
			document.execCommand('copy');
			document.body.removeChild(dummy);
			$('body').append('<div id="alertCopy" class="alert alert-success alertCopy"><strong>'+Content.linkCopied+'</strong></div>');
			$('#alertCopy').show().delay(1500).fadeOut();
			setTimeout(function(){
  			$('#alertCopy').remove();
			}, 2000); /*time to show the notification plus the time to do the fadeout effect*/ 			
 		},
 		showPageOptions: function(){
		              uglipop({
		                class:'modalReplay noprint scrollModal PagSpec', //styling class for Modal
		                source:'html',
		                content:'<button onclick="ARQUIVO.closeUglipopCustomCss()" class="expand__close__white" title="Fechar"></button>'+
				                '<div class="main-menu-top-div">'+
							    	'<h4 id="menuUrl" title="'+_url+'">'+ _url+'</h4>' +
							  		'<h5 id="menuTs">'+ this.getShortDatets() +'</h5>' + 			                             
							  	'</div>'+
							  	'<div class="fullwidth menu">'+
									'<a href="//'+_hostname+'/search.jsp?l='+Content.language+'&query='+encodeURIComponent(_url)+'" onclick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'ListVersionsClick\', \'arquivo.pt/'+_ts+'/'+_url+'\');"><h4><i class="fa fa-list" aria-hidden="true"></i> '+Content.allVersions+'</h4></a>'+ 						                      
									'<a href="#" id="a_moreinfo" title="'+Content.moreInfoIcon+'"><h4><i class="fa fa-info-circle right-9" aria-hidden="true"></i> '+Content.moreInfoIcon+'</h4></a>' +									
             						'<a id="screenshotOption"><h4><i class="fa fa-camera right-5" aria-hidden="true"></i> '+Content.saveImage+'</h4></a>' +
			 						'<a id="printOption"><h4><i class="fa fa-print right-7" aria-hidden="true"></i> '+Content.print+'</h4></a>'+									
			 						'<a id="a_reconstruct" alt="'+Content.completePage+'" href=javascript:void(0) onclick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'Complete Page\', \'arquivo.pt/'+_ts+'/'+_url+'\'); ARQUIVO.attachCompletePageModal();"><h4><i class="complete-page"></i><span class="complete-page-text"> '+Content.completePage+'</span></h4></a>'+
			 						'<a id="expandPage"  href="/noFrame/replay/'+_ts+'/'+_url+'" onclick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'ExpandClick\', \'arquivo.pt/'+_ts+'/'+_url+'\');"><h4><i class="ion ion-arrow-resize right-8" aria-hidden="true"></i> '+Content.expandPage+'</h4></a>'+
								'</div>'+
		                        '<div></div>'
		              });
		              $( ".scrollModal" ).ready(function() {
		                $( ".scrollModal" ).parent().css({
		                    'top': 'inherit',
		                    'left': 'inherit',
		                    'bottom': '47px',
		                    'width': '100%',
		                    'max-height': '80%',	                    
		                    'opacity': '1',  
		                    'overflow': 'auto' ,
		                    'transform': 'none',
		                    '-webkit-transform': 'none',
		                    '-ms-transform': 'unset'
		                });
		              }); 
		              ARQUIVO.attachClosePopup();
                	  $('#a_moreinfo').on('click', function(e){         
        				ARQUIVO.moreInfoModal();        
      				  });  


 		},
 		attachCompletePageModal: function(){
        
	       //this.goToContent();  
	       this.completePageModal();        
     	
		},
 		completePageModal: function(){
		  	ga('send', 'event', 'ReplayBarFunctions', 'Reconstruct', 'arquivo.pt/'+_ts+'/'+_url);
		  	var classModalTitle = "";
		  	if(_language === 'pt')
		  		classModalTitle = "completePageIcon";
		  	else
		  		classModalTitle = "completePageIconEN";
		    uglipop({
		      class:'modalReplay noprint', //styling class for Modal
		      source:'html',
		      content: '<h4 class="modalTitleComplete" id="'+classModalTitle+'">'+Content.leavingArquivo+'</h4>' +
		              '<div class="row"><a id="completePage" class="col-xs-6 text-center leftAnchor modalOptions">OK</a><a id="cancelPopup" class="col-xs-6 text-center modalOptions">'+Content.cancel+'</a></div>'});               
		  	this.attachCompletepage();
		  	this.attachClosePopup();
		},
		attachCompletepage: function(){
		    $('#completePage').on('click', function(e){
		        ga('send', 'event', 'Complete Page', 'Clicked complete page and confirmed', 'arquivo.pt/'+_ts+'/'+_url);
		        window.open('https://timetravel.mementoweb.org/reconstruct/'+_ts+'/'+_url);
		        ARQUIVO.closeUglipop();
		    });    
		},
		attachClosePopup: function(){
		  $('#cancelPopup').on('click', function(e){
		    ARQUIVO.closeUglipop();
		  });         
		},
		closeUglipop: function(){
		  $('#uglipop_content_fixed').fadeOut();
		  $('#uglipop_overlay').fadeOut('fast');
		},
		replayWithOldBrowsers: function() {
			ga('send', 'event', 'ReplayBarFunctions', 'Replay with old browser', 'arquivo.pt/'+_ts+'/'+_url);
		    uglipop({
		      class:'modalReplay noprint', //styling class for Modal
		      source:'html',
		      content: '<h4 class="modalTitleReplayWithOldBrowsers">'+Content.leavingArquivo+'</h4>' +
		              '<div class="row"><a id="okReplayWithOldBrowsers" class="col-xs-6 text-center leftAnchor modalOptions">OK</a><a id="cancelPopup" class="col-xs-6 text-center modalOptions">'+Content.cancel+'</a></div>'});               
		  	this.attachReplayWithOldBrowsers();
		  	this.attachClosePopup();
		},
		attachReplayWithOldBrowsers: function() {
			$('#okReplayWithOldBrowsers').on('click', function(e) {
		        ga('send', 'event', 'Replay with old browser', 'Clicked replay with old browser and confirmed', 'arquivo.pt/'+_ts+'/'+_url);
		        window.open('http://oldweb.today/firefox/'+_ts+'/'+_url);
		        ARQUIVO.closeUglipop();
		    });
		},
 		updateInfo: function(url, ts, patching){
 			_url = url;
 			_ts = ts;
			/*get new page title and update it*/  
			var title = $("#replay_iframe").contents().find("meta[property='og:title']").attr("content");
			if(title === undefined || title === null) // there is no og:title meta tag in this iframe
			{
			  title = $("#replay_iframe").contents().find("title").html(); //search for a title tag in the iframe
			  if (title === undefined || !title.length){ //there is no title 
			      title = "Arquivo.pt"/*Content.shareMessage;*/
			  }
			}
			title = title + " - preservado pelo Arquivo.pt"/*Content.preservedByArquivo*/;
			document.title = title;

			var addthis_config = addthis_config||{};
			addthis_config.data_track_addressbar = false;
			addthis_config.data_track_clickback = false;

			$('#expandPage').attr('href', '/noFrame/replay/'+_ts+'/'+_url);
			$('#expandPage').attr('onclick', 'ga(\'send\', \'event\', \'ReplayBarFunctions\', \'ExpandClick\', \'arquivo.pt/'+_ts+'/'+_url+'\')');

			$('#menuUrl').attr('title', _url);
			$('#menuUrl').html(_url); /*update menu url*/
			$('#menuTs').html(ARQUIVO.getShortDatets()); /*update menu ts*/

			_patching = patching;
			ARQUIVO.updatePageOnUrlSearch(url, ts);

			ga('send', 'pageview'); /*New page*/ 			
 		},
 		createSlideMenu: function(){

 			this.insertMenuHtlm();

		    var replayMenu = document.querySelector('#replayMenuButton');
		    var openReplayMenu = function () {
		      swiper.slideNext();
		      $('#mainMask').fadeIn('fast');
		    };

		    var menuButton = document.querySelector('#menuButton');
		    var openMenu = function () {
		      swiper.slidePrev();
		    };
		    swiper = new Swiper('.swiper-container', {
		      slidesPerView: 'auto',
		      initialSlide: 1,
		      resistanceRatio: 0,
		      slideToClickedSlide: true,
		      on: {
		        slideChangeTransitionStart: function () {
		          var slider = this;
		          if (slider.activeIndex === 0) { /*open menu*/
		          	$('#mainMask').fadeIn('fast');
		            menuButton.classList.add('open');
		            $('.swiper-container').removeClass('swiper-no-swiping');
		            // required because of slideToClickedSlide
		            menuButton.removeEventListener('click', openMenu, true);
		          } else  if (slider.activeIndex === 1) { /*close menu*/
		          	$('.swiper-container').addClass('swiper-no-swiping');
		          	$('#mainMask').fadeOut('fast');
		            menuButton.classList.remove('open');
		          
		          // can not make ionic return the replay menu has activeIndex with 2 value, so the following if dead code.
		          } else if(slider.activeIndex === 2){
		          	$('#mainMask').fadeIn('fast');
		          }
		        }
		        , slideChangeTransitionEnd: function () {
		          var slider = this;
		          if (slider.activeIndex === 1) {
		            menuButton.addEventListener('click', openMenu, true);
		            replayMenu.addEventListener('click', openReplayMenu, true);
		          }		         
		        },
		      }
		    });
		    swiper.allowSlidePrev = true;
		    swiper.allowSlideNext = true;
 		},

 		insertMenuHtlm: function(){
 			$('.swiper-wrapper').prepend(
			  '		  <div class="swiper-slide menu swiper-slide-prev">' +
			  		   '<div class="main-menu-top-div">'+
			  		   	 '<h4>&nbsp;</h4>'+
			  	         '<button href="#" onclick="ARQUIVO.goToContent()" class="close-functions clean-button-no-fill">&#10005;</button>' +
			  	       '</div>'+
              '		 	<a id="changeLanguage" onclick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'ChangeLanguageTo'+Content.otherLanguage+'Click\', \'arquivo.pt/'+_ts+'/'+_url+'\');"><h4><i class="fa fa-flag right-6" aria-hidden="true"></i> '+Content.otherLanguageExtended+'</h4></a>'+
			  '			<button class="clean-button" onclick="ARQUIVO.copyLink();"><h4><i class="fa fa-link padding-right-menu-icon" aria-hidden="true"></i> '+Content.copyLink+'</h4></button>' +
  					   '<button class="clean-button" id="pagesMenu" onclick="ARQUIVO.pagesClick();"><h4><i class="fa fa-globe padding-right-menu-icon" aria-hidden="true"></i> '+Content.pages+'<i id="pagesCarret" class="fa fa-caret-down iCarret shareCarret pull-right" aria-hidden="true"></i></h4></button>'+	 			  
      				   '<div id="pageOptions">'+
              ' 			<a href="/index.jsp?l='+Content.language+'" onclick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'NewSearchClick\', \'arquivo.pt/'+_ts+'/'+_url+'\');"><h4 class="submenu"><i class="fa fa-search right-7" aria-hidden="true"></i> '+Content.newSearch+'</h4></a>' +
              ' 			<a href="//'+_hostname+'/advanced.jsp?l='+Content.language+'" onclick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'AdvancedSearchClick\', \'arquivo.pt/'+_ts+'/'+_url+'\');"><h4 class="submenu"><i class="fa fa-search-plus right-7" aria-hidden="true"></i> '+Content.advancedSearch+'</h4></a>' +
              		   '</div>'+
			  		   '<button class="clean-button" id="imagesMenu" onclick="ARQUIVO.imagesClick();"><h4><i class="fa fa-image padding-right-menu-icon" aria-hidden="true"></i> '+Content.images+'<i id="imagesCarret" class="fa iCarret shareCarret pull-right fa-caret-down" aria-hidden="true"></i></h4></button>'+
      				   '<div id="imageOptions">'+
              ' 			<a href="/images.jsp?l='+Content.language+'" onclick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'NewImageSearchClick\', \'arquivo.pt/'+_ts+'/'+_url+'\');"><h4 class="submenu"><i class="fa fa-search right-7" aria-hidden="true"></i> '+Content.newSearch+'</h4></a>' +
              ' 			<a href="/advancedImages.jsp?l='+Content.language+'" onclick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'AdvancedImageSearchClick\', \'arquivo.pt/'+_ts+'/'+_url+'\');"><h4 class="submenu"><i class="fa fa-search-plus right-7" aria-hidden="true"></i> '+Content.advancedSearch+'</h4></a>' +
              		   '</div>'+                
              '		 	<a id="switchDesktop" href="" onclick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'SwitchDesktopClick\', \'arquivo.pt/'+_ts+'/'+_url+'\');"><h4><i class="fa fa-desktop right-8" aria-hidden="true"></i> '+Content.switchDesktop+'</h4></a>'+			                    
			  '		 	<a id="reportBug"><h4><i class="fa fa-bug right-10" aria-hidden="true"></i> '+Content.report+'</h4></a>'+              
              '		 	<a href="'+Content.aboutHref+'" onclick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'AboutClick\', \'arquivo.pt/'+_ts+'/'+_url+'\');"><h4><i class="fa fa-info-circle right-10" aria-hidden="true"></i> '+Content.about+'</h4></a>'+
              '		</div>' ); 			
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
		    window.open('//'+_hostname+'/screenshot/?url='+encodeURIComponent("https://"+_hostname+"/noFrame/replay/"+ _ts+'/'+_url)+"&width="+window.screen.width/*window.innerWidth*/+"&height="+/*window.innerHeight*/ window.screen.height);
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
		    ARQUIVO.getImageToPrint("https://"+_hostname+"/noFrame/replay/"+ _ts+"/"+_url);
		  }); 			
 		},  		 		 				
 		attachShare: function(){
		  $('#shareMenu').on('click', function(e){
		  	ga('send', 'event', 'ReplayBarFunctions', 'ShareMenuClick', '//arquivo.pt/'+_ts+'/'+_url);
		    $('#shareCarret').toggleClass('fa-caret-up fa-caret-down');
		    $('#shareOptions').slideToggle( "fast", "linear" );
		  }); 	 			
 		}, 	
 		attachTools: function(){
		  $('#toolsMenu').on('click', function(e){
		  	ga('send', 'event', 'ReplayBarFunctions', 'ToolsMenuClick', '//arquivo.pt/'+_ts+'/'+_url);		  	
		    $('#toolsCarret').toggleClass('fa-caret-up fa-caret-down');
		    $('#toolsOptions').slideToggle( "fast", "linear" );
		  }); 	 			
 		}, 	 			
 		attachSwitchDesktop: function(){
		  $('#switchDesktop').on('click', function(e){		  	
		  	e.preventDefault();
		  	ga('send', 'event', 'ReplayBarFunctions', 'SwitchDesktopClick', '//arquivo.pt/'+_ts+'/'+_url);	
			Cookies.set('forceDesktop', 'true', { domain: window.location.hostname.substr(2, window.location.hostname.length), path:'djsakj' });
			/*redirect current link from mobile to desktop version i.e. remove the m. from current link*/
			window.location = window.location.href.replace(window.location.hostname , window.location.hostname.substr(2, window.location.hostname.length)); 
		  }); 	 			
 		},
		moreInfoModal: function(){
		  ga('send', 'event', 'ReplayBarFunctions', 'MoreInformationMenuClick', '//arquivo.pt/'+_ts+'/'+_url);
		    var requestURL = "//"+window.location.hostname.replace("m.","")+ "/textsearch";
		    metadataResponse= '';
		      $.ajax({
		      // example request to the cdx-server api - 'http://arquivo.pt/textsearch?metadata=http%3A%2F%2Fquiz.musicbox.sapo.pt%2F%2F20131108093638'
		          url: requestURL,
		          data: {
		            metadata: _url+"/"+_ts
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

		              uglipop({
		                class:'modalReplay noprint scrollModal PageSpec', //styling class for Modal
		                source:'html',
		                content:'<button id="removeModal" class="expand__close" title="Fechar"></button>'+
		                        '<h4 class="modalTitle"><i  alt="'+Content.moreInfoIcon+'" class="ion ion-information-circled menu-icon removeContentIcon"></i> '+Content.moreInfoIcon+' <a target="_blank" href="https://github.com/arquivo/pwa-technologies/wiki/Arquivo.pt-API-v.0.2#response-fields">'+Content.techDetails+'</a></h4>'+
		                        '<div>' + metadataResponse + '</div>'
		              });
		              ARQUIVO.attachRemoveModal();
		              $( ".scrollModal" ).ready(function() {
		                $( ".scrollModal" ).parent().css({
		                    'top': '2%',
		                    'left': '3%',
		                    'bottom': '1%',
		                    'width': '94%',
		                    'height': '96%', 
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
		}, 		
		attachMoreInfoModal: function(){
       		$('#a_moreinfo').on('click', function(e){         
        		ARQUIVO.moreInfoModal();        
      		});    			
		},
		attachRemoveModal: function(){
		       $('#removeModal').on('click', function(e){    
		          ARQUIVO.closeUglipopCustomCss();  
		        });
		       $('#uglipop_overlay').on('click', function(e){
		          if( $('#uglipop_popbox').hasClass('scrollModal')){
		            ARQUIVO.closeUglipopCustomCss();
		          }
		       });    
		},
		closeUglipopCustomCss: function(){
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
		     	localStorage.setItem('language', 'EN');
		        window.location.reload();
		     }
		    else //default language Portuguesez
		    {
		        localStorage.setItem('language', 'PT');   
		        window.location.reload();
		    }   
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

			var requestURL = screenshotEndpoint + "?url=" + encodedURLToPrint + "&download=false";

			let divPrintMe = document.getElementById("divPrintMe");
			let imgElem = document.getElementById("imgToPrint");

			if (imgElem == null){
				imgElem = document.createElement('img');
				imgElem.setAttribute("id", "imgToPrint");
				imgElem.setAttribute("width", "600px");
				imgElem.style.display = 'inherited';
				divPrintMe.appendChild(imgElem);
			}

			imgElem.addEventListener('load', () => {
				setTimeout(() => {
					window.print();
				}, 1000);
			});

			imgElem.src = requestURL;
			divPrintMe.style.display = "block";

			ARQUIVO.loadingModal();
			console.log(this.url);
		},
		pagesClick: function(){
		    $('#pagesCarret').toggleClass('fa-caret-up fa-caret-down');
		    $('#pageOptions').slideToggle( "fast", "linear" );
		},
		imagesClick: function(){
		    $('#imagesCarret').toggleClass('fa-caret-up fa-caret-down');
		    $('#imageOptions').slideToggle( "fast", "linear" );
		},
		printModal: function(){
			ga('send', 'event', 'ReplayBarFunctions', 'PrintMenuClick', 'arquivo.pt/'+_ts+'/'+_url);
		    uglipop({
		      class:'modalReplay noprint', //styling class for Modal
		      source:'html',
		      content:'<h4 class="modalTitle"><i class="fa fa-print" aria-hidden="true"></i> '+Content.printModalTitle+'</h4>'+
		              '<div class="row"><a id="printPage" onclick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'PrintMenuConfirm\', \'arquivo.pt/'+_ts+'/'+_url+'\');" class="col-xs-6 text-center leftAnchor modalOptions">OK</a><a id="cancelPopup" onclick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'PrintMenuCancel\', \'arquivo.pt/'+_ts+'/'+_url+'\');" class="col-xs-6 text-center modalOptions">'+Content.cancel+'</a></div>'});
		    this.attachPrint();          			
		    this.attachClosePopup();
		},
		screenshotModal: function(){
			ga('send', 'event', 'ReplayBarFunctions', 'ScreenshotMenuClick', 'arquivo.pt/'+_ts+'/'+_url);			
		    uglipop({
		      class:'modalReplay noprint', //styling class for Modal
		      source:'html',
		      content:'<h4 class="modalTitle"><i class="fa fa-camera" aria-hidden="true"></i> '+Content.saveAsImage+'</h4>'+
		              '<div class="row"><a id="takeScreenshot" onclick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'ScreenshotMenuConfirm\', \'arquivo.pt/'+_ts+'/'+_url+'\');" class="col-xs-6 text-center leftAnchor modalOptions">OK</a><a id="cancelPopup" onclick="ga(\'send\', \'event\', \'ReplayBarFunctions\', \'ScreenshotMenuCancel\', \'arquivo.pt/'+_ts+'/'+_url+'\');" class="col-xs-6 text-center modalOptions">'+Content.cancel+'</a></div>'});
		    this.attachScreenshot();          			
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
		attachReportBug: function(){
			$('#reportBug').click( function(e) {
				e.preventDefault();
				ga('send', 'event', 'ReplayBarFunctions', 'ReportBug', window.location.href);
				window.location = Content.bug + window.location.href.replaceAll('&', '%26');
			});
		},		 		
		closeSwipeMenu: function(){
		},
		attachKeyBoardEvent: function() {
			if (document.onkeydown == null) {
				document.onkeydown = function(evt) {
				  // When pressing escape key close image
				  var isEscape = false;
				  if ("key" in evt) {
				      isEscape = (evt.key === "Escape" || evt.key === "Esc");
				  } else {
				      isEscape = (evt.keyCode === 27);
				  }
				  if (isEscape) {
				      ARQUIVO.goToContent();
				  }
				}
			}
		},
        // called from url search iframe when the user clicks a specific version
        // the message is the url clicked
		urlSearchClickOnVersion: function(waybackUrlClicked) {
			const timestampAndURL = waybackUrlClicked.substring(wbinfo.prefix.length);
			const timestampURLSeparatorPos = timestampAndURL.indexOf('/');
			const timestamp = timestampAndURL.substring(0, timestampURLSeparatorPos);
			const url = timestampAndURL.substring(timestampURLSeparatorPos+1);
			var frameSrc = wbinfo.prefix + timestamp + 'mp_/' + url;
			$('#replay_iframe').attr('src', frameSrc); //update the iframe to the new version
		},
	    // function that updates
	    updatePageOnUrlSearch: function(url, timestamp) {
	    	function getIframeWindow(iframe_object) {
			  var doc;

			  if (iframe_object.contentWindow) {
			    return iframe_object.contentWindow;
			  }

			  if (iframe_object.window) {
			    return iframe_object.window;
			  } 

			  if (!doc && iframe_object.contentDocument) {
			    doc = iframe_object.contentDocument;
			  } 

			  if (!doc && iframe_object.document) {
			    doc = iframe_object.document;
			  }

			  if (doc && doc.defaultView) {
			   return doc.defaultView;
			  }

			  if (doc && doc.parentWindow) {
			    return doc.parentWindow;
			  }

			  return undefined;
			}

			async function doUpdate(iframeId, url, timestamp) {
		    	const ifrm_el = document.getElementById(iframeId);
		    	if (ifrm_el) {
			    	const ifrm_win = getIframeWindow(ifrm_el);
			    	if (ifrm_win && ifrm_win.replacePageAndHighlightTimestamp) { // the function could be not defined because the iframe could be starting up.
			    		ifrm_win.replacePageAndHighlightTimestamp(url, timestamp);
			    	}
		    	}
			}
			doUpdate("url_search_iframe", url, timestamp);
	    }
    };
}());

