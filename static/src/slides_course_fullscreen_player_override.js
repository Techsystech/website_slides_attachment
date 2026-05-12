/** @odoo-module **/

import { renderToElement } from "@web/core/utils/render";
import Fullscreen from "@website_slides/js/slides_course_fullscreen_player";

Fullscreen.include({
    /**
     * Render local video slides in fullscreen using a native <video> element.
     *
     * @private
     * @override
     */
    _renderSlide: async function () {
        // Let the base handle quiz / standard video types first.
        var def = await this._super.apply(this, arguments);

        const slide = this._slideValue;
        if (slide.category !== 'video') {
            return def;
        }

        // The base method only knows youtube / vimeo / google_drive.
        // For local videos it renders nothing, so we fill the content here.
        const isLocal = slide.videoSourceType === 'local' || slide.isLocalVideo;

        console.log('[website_slides_attachment] _renderSlide check', {
            id: slide.id,
            category: slide.category,
            videoSourceType: slide.videoSourceType,
            isLocalVideo: slide.isLocalVideo,
            isLocal: isLocal,
        });

        if (!isLocal) {
            return def;
        }

        var $content = this.$('.o_wslides_fs_content');
        console.log('[website_slides_attachment] $content length:', $content.length, 'html before:', $content.html());

        // Try renderToElement first
        var renderedEl = null;
        try {
            renderedEl = renderToElement('website.slides.fullscreen.content.video', {widget: this});
            console.log('[website_slides_attachment] renderToElement returned:', renderedEl, 'type:', typeof renderedEl, 'nodeType:', renderedEl ? renderedEl.nodeType : 'n/a');
        } catch (e) {
            console.error('[website_slides_attachment] renderToElement failed:', e);
        }

        if (renderedEl) {
            $content.empty().append(renderedEl);
        } else {
            // Fallback: build the DOM manually so we can see if the issue is template rendering
            console.warn('[website_slides_attachment] renderToElement returned nothing, using manual DOM fallback');
            var srcUrl = '/website_slides_attachment/download/' + slide.id + '/filename=' + encodeURIComponent((slide.name || 'local-video') + '.mp4');
            var wrapper = document.createElement('div');
            wrapper.className = 'ratio h-100';
            var video = document.createElement('video');
            video.id = 'embeddedVideoViewer';
            video.className = 'o-FileViewer-view';
            video.setAttribute('controls', 'controls');
            video.setAttribute('preload', 'metadata');
            var source = document.createElement('source');
            source.setAttribute('src', srcUrl);
            source.setAttribute('type', 'video/mp4');
            video.appendChild(source);
            video.appendChild(document.createTextNode('Your browser does not support the video tag.'));
            wrapper.appendChild(video);
            $content.empty().append(wrapper);
        }

        console.log('[website_slides_attachment] $content html after:', $content.html());

        const videoViewer = document.querySelector('#embeddedVideoViewer');
        if (videoViewer) {
            videoViewer.addEventListener('ended', async (event) => {
                await this.trigger_up('slide_mark_completed', slide);
                await this.trigger_up('slide_go_next', slide);
            });
        } else {
            console.warn('[website_slides_attachment] #embeddedVideoViewer not found after render');
        }

        return def;
    },
});