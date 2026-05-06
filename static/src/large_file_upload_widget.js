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
        alert('Please save the slide before uploading a local video.');
        return;
      }
      try {
        const formData = new FormData();
        formData.append('file', this.state.file);
        formData.append('res_id', this.props.record.resId);
        formData.append('csrf_token', odoo.csrf_token);

        this.state.uploading = true;
        const response = await fetch('/website_slides_attachment/upload', {
          method: 'POST',
          body: formData,
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.error || response.statusText);
        }
        const changes = { [this.props.name]: payload.token };
        await this.props.record.update(changes, { save: this.props.autosave });
        this.state.uploading = false;
      }
      catch (error) {
        this.state.uploading = false;
        alert('Upload Failed with error: ' + error.message);
      }
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
