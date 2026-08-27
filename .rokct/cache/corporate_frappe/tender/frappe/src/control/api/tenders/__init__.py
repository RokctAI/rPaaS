# Copyright (c) 2026 RokctAI
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# This file uses the composer's literal {app_name} template placeholder in
# imports (fleet SDK convention, cf. polaris) - it only parses after
# composition substitutes the real app package name.
# compliance-ignore-file: syntax-error

from {app_name}.tender.control.api.tenders.get_tender_workflow_template import get_tender_workflow_template
from {app_name}.tender.control.api.tenders.get_relevant_tenders import get_relevant_tenders
from {app_name}.tender.control.api.tenders.get_relevant_grants import get_relevant_grants
from {app_name}.tender.control.api.tenders.get_relevant_equity import get_relevant_equity
from {app_name}.tender.control.api.tenders.get_tender_detail import get_tender_detail
from {app_name}.tender.control.api.tenders.claim_tender import claim_tender
from {app_name}.tender.control.api.tenders.get_my_bids import get_my_bids
from {app_name}.tender.control.api.tenders.update_bid_status import update_bid_status
from {app_name}.tender.control.api.tenders.update_checklist_item import update_checklist_item
