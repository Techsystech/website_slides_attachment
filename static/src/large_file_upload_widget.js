/** @odoo-module */

import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export class UploadWidget extends Component {
   static template = "website_slides_attachment.large_file_upload_widget_template";
   static props = {
        ...standardFieldProps,
        acceptedFileExtensions: { type: String, optional: true },
        fileNameField: { type: String, optional: true },
   };

   setup() {
      this.state = useState({
        file: null,
        filename: null,
        uploading: false,
        progress: 0,
      });
   }

    onFileChange(event) {
      this.state.filename = event.target.files[0]?.name || null;
      this.state.file = event.target.files[0] || null;
    }

    async startUpload() {
      if (!this.state.file) {
        alert('Please select a file to upload.');
        return;
      }
      if (!this.props.record.resId) {
        // Auto-save the new record so it gets an ID before we create an
        // attachment that needs res_model/res_id.
        const saved = await this.props.record.save();
        if (!saved) {
          alert('Please fill in the required fields before uploading a local video.');
          return;
        }
      }
      const formData = new FormData();
      formData.append('file', this.state.file);
      formData.append('res_id', this.props.record.resId);
      formData.append('csrf_token', odoo.csrf_token);

      this.state.uploading = true;
      this.state.progress = 0;

      try {
        const payload = await this._uploadWithProgress(formData);
        const changes = { [this.props.name]: payload.token };
        await this.props.record.update(changes, { save: this.props.autosave });
        this.state.uploading = false;
        this.state.progress = 0;
        this.state.file = null;
        this.state.filename = null;
      } catch (error) {
        this.state.uploading = false;
        this.state.progress = 0;
        alert('Upload Failed with error: ' + error.message);
      }
    }

    _uploadWithProgress(formData) {
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.upload.addEventListener('progress', (event) => {
          if (event.lengthComputable) {
            this.state.progress = Math.round((event.loaded / event.total) * 100);
          }
        });
        xhr.addEventListener('load', () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            try {
              resolve(JSON.parse(xhr.responseText));
            } catch (e) {
              reject(new Error('Invalid server response'));
            }
          } else {
            let msg = xhr.statusText;
            try {
              const payload = JSON.parse(xhr.responseText);
              msg = payload.error || msg;
            } catch (e) {}
            reject(new Error(msg));
          }
        });
        xhr.addEventListener('error', () => reject(new Error('Network error')));
        xhr.addEventListener('abort', () => reject(new Error('Upload aborted')));
        xhr.open('POST', '/website_slides_attachment/upload');
        xhr.send(formData);
      });
    }

    async onRemove(){
      const formData = new FormData();
      formData.append('attachment_token', this.props.record.data[this.props.name]);
      formData.append('csrf_token', odoo.csrf_token);

      await fetch('/website_slides_attachment/remove', {
        method: 'POST',
        body: formData,
      });

      const changes = { [this.props.name]: '' };
      await this.props.record.update(changes, { save: this.props.autosave });
      this.state.file = null;
      this.state.filename = null;
    }
}

export const uploadWidget = {
    component: UploadWidget,
    displayName: _t("File"),
    supportedOptions: [
        {
            label: _t("Accepted file extensions"),
            name: "accepted_file_extensions",
            type: "string",
        },
    ],
    supportedTypes: ["char"],
    extractProps: ({ attrs, options }) => ({
        acceptedFileExtensions: options.accepted_file_extensions,
        fileNameField: attrs.filename,
    }),
};
registry.category("fields").add("large_file_upload_widget", uploadWidget);
