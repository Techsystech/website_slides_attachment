/** @odoo-module **/

import { renderToElement } from "@web/core/utils/render";
import Fullscreen from "@website_slides/js/slides_course_fullscreen_player";
import { unhideConditionalElements } from '@website/js/content/inject_dom';

Fullscreen.include({
    /**
     *
     * @private
     * @override
     */
    _renderSlide: async function () {//coppied from the slides_course_fullscreen_player.js with the minor ajustment to use the video player
            // Avoid concurrent execution of the slide rendering as it writes the content at the same place anyway.
            if (this._renderSlideRunning) { return; }
            this._renderSlideRunning = true;
            try {
                const slide = this._slideValue;
                var $content = this.$('.o_wslides_fs_content');
                $content.empty();
                if (this.websiteAnimateWidget) {
                    this.websiteAnimateWidget.destroy()
                    this.websiteAnimateWidget = null;
                }

                // display quiz slide, or quiz attached to a slide
                if (slide.category === 'quiz' || slide.isQuiz) {
                    $content.addClass('bg-white');
                    var QuizWidget = new Quiz(this, slide, this.channel);
                    return await QuizWidget.appendTo($content);
                }

                // render slide content
                
                if (slide.category === 'video' && slide.videoSourceType === 'local') {
                    $content.empty().append(renderToElement('website.slides.fullscreen.content.video', {widget: this}));
                    const videoViewer = document.querySelector('#embeddedVideoViewer')
                    videoViewer.addEventListener('ended', (event) => {
                        this.trigger_up('slide_mark_completed', slide);
                        this.trigger_up('slide_go_next', slide);
                    });
                }
                else if (['document', 'infographic'].includes(slide.category)) {
                    $content.empty().append(renderToElement('website.slides.fullscreen.content', {widget: this}));
                } else if (slide.category === 'video' && slide.videoSourceType === 'youtube') {
                    this.videoPlayer = new VideoPlayerYouTube(this, slide);
                    return await this.videoPlayer.appendTo($content);
                } else if (slide.category === 'video' && slide.videoSourceType === 'vimeo') {
                    this.videoPlayer = new VideoPlayerVimeo(this, slide);
                    return await this.videoPlayer.appendTo($content);
                } else if (slide.category === 'video' && slide.videoSourceType === 'google_drive') {
                    $content.empty().append(renderToElement('website.slides.fullscreen.video.google_drive', {widget: this}));
                } else if (slide.category === 'article'){
                    this.websiteAnimateWidget = new publicWidget.registry.WebsiteAnimate();
                    var $wpContainer = $('<div>').addClass('o_wslide_fs_article_content bg-white block w-100 overflow-auto p-3');
                    $wpContainer.html(slide.htmlContent);
                    $content.append($wpContainer);
                    this.trigger_up('widgets_start_request', {
                        $target: $content,
                    });
                    this.websiteAnimateWidget.attachTo($wpContainer);
                }
                unhideConditionalElements();
            } finally {
                this._renderSlideRunning = false;
            }
        },
});