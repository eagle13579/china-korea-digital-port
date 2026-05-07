// 管理员页面英文翻译（PRD-010）
(function() {
    if (typeof translations === 'undefined') {
        // Wait for main.js to load
        document.addEventListener('DOMContentLoaded', function() {
            if (typeof translations !== 'undefined') {
                addAdminEnglish();
            }
        });
    } else {
        addAdminEnglish();
    }

    function addAdminEnglish() {
        var enData = {
            // funnel.html
            funnel_title: 'Sales Funnel',
            funnel_subtitle: 'China-Korea Digital Port · Sales Funnel Management',
            funnel_back: '← Back to Admin',
            funnel_refresh: 'Refresh',
            funnel_empty: 'No data',
            funnel_quote_title: 'Generate Quote',
            funnel_quote_lead: 'Lead',
            funnel_quote_select: 'Select Plan',
            funnel_quote_generate: 'Generate & Send Quote',
            plan_free: 'Free Assessment ¥0',
            plan_depth: 'Depth Plan ¥9,800',
            plan_annual: 'Annual Subscription ¥58,000',
            cancel: 'Cancel',
            loading: 'Loading...',
            // quote.html
            quote_title: 'Quote Management',
            quote_subtitle: 'China-Korea Digital Port · Quote Management',
            quote_back_funnel: '← Back to Funnel',
            quote_back_admin: '← Back to Admin',
            quote_total: 'Total Quotes',
            quote_draft: 'Draft',
            quote_sent: 'Sent',
            quote_accepted: 'Accepted',
            quote_list: 'Quote List',
            quote_empty: 'No quotes yet',
            quote_no: 'Quote No.',
            quote_lead: 'Lead',
            quote_company: 'Company',
            quote_plan: 'Plan',
            quote_price: 'Amount',
            quote_status: 'Status',
            quote_time: 'Time',
            quote_action: 'Action',
            quote_send_btn: 'Send',
            quote_accept_btn: 'Accept',
            quote_reject_btn: 'Reject',
        };
        if (!translations['en']) translations['en'] = {};
        Object.assign(translations['en'], enData);
    }
})();
