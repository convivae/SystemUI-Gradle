# Copyright (C) 2026 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

# If you don't need to do a full clean build but would like to touch
# a file or delete some intermediate files, add a clean step to the end
# of the list.  These steps will only be run once, if they haven't been
# run before.

$(call add-clean-step, rm -rf $(PRODUCT_OUT)/system/product/priv-app/SystemUI)
$(call add-clean-step, rm -rf $(PRODUCT_OUT)/product/priv-app/SystemUI)
