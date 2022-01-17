$(function(){
    $('#replay-left-nav').on('click', '.accordion-header', function (e) {
        e.preventDefault();
        e.stopPropagation();
        let $this = $(this);
        if ($this.next().hasClass('show')) {
            $this.removeClass('active');
            $this.next().removeClass('show');
            $this.next().slideUp(150);
        } else {
            $this.addClass('active');
            $this.next().addClass('show');
            $this.next().slideDown(150);
        }
    });
});