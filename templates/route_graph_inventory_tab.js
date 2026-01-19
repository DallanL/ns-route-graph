(function() {
    'use strict';

    // CONFIGURATION
    var apiEndpoint = '{{ api_endpoint }}'; 
    var cytoscapeCdn = 'https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.28.1/cytoscape.min.js';

    // 1. DYNAMIC LOADER
    function ensureCytoscapeLoaded(callback) {
        if (window.cytoscape) {
            callback();
        } else {
            console.log('Loading Cytoscape.js...');
            var script = document.createElement('script');
            script.src = cytoscapeCdn;
            script.onload = callback;
            document.head.appendChild(script);
        }
    }

    // 2. DATA FETCHER
    function loadGraphData() {
        var token = localStorage.getItem("ns_t");
        
        // Strict variable checks
        if (typeof current_domain === 'undefined' || !current_domain) {
            $('#cy_container').html('<div class="alert alert-danger" style="margin:20px;">Error: "current_domain" is not defined. Cannot determine PBX domain.</div>');
            return;
        }
        if (typeof server_name === 'undefined' || !server_name) {
            $('#cy_container').html('<div class="alert alert-danger" style="margin:20px;">Error: "server_name" is not defined. Cannot determine API URL.</div>');
            return;
        }

        var domain = current_domain;
        var apiUrl = server_name;

        console.log("Fetching graph for domain:", domain);

        // Show Loading Animation
        $('#cy_container').html(
            '<div style="width:100%; height:100%; display:flex; align-items:center; justify-content:center; flex-direction:column; color:#666;">' +
            '<i class="fa fa-spinner fa-spin fa-3x fa-fw"></i>' +
            '<span style="margin-top:15px; font-size:16px; font-weight:bold;">Building Call Flow Graph...</span>' +
            '<span style="margin-top:5px; font-size:12px;">This may take a few seconds.</span>' +
            '</div>'
        );

        $.ajax({
            url: apiEndpoint,
            method: 'GET',
            data: { domain: domain , token: token , api_url: apiUrl},
            success: function(data) {
                $('#cy_container').empty(); // Clear loader
                renderCytoscape(data);
                populateDidFilter(data);
            },
            error: function(err) {
                var msg = (err.responseJSON && err.responseJSON.detail) ? err.responseJSON.detail : err.statusText;
                $('#cy_container').html('<div class="alert alert-danger" style="margin:20px;">API Error: ' + msg + '</div>');
                console.error("Route Graph API Error:", err);
            }
        });
    }

    // 3. RENDERER
    function renderCytoscape(graphData) {
        var container = document.getElementById('cy_container');
        if (!container) return;

        console.log("Rendering Graph...");

        window.cy = cytoscape({
            container: container,
            elements: graphData, 
            boxSelectionEnabled: true,
            autounselectify: false,
            minZoom: 0.1,
            maxZoom: 3.0,
            wheelSensitivity: 0.2,
            style: [
                {
                    selector: 'node',
                    style: {
                        'background-color': 'data(bg)',
                        'label': 'data(label)',
                        'color': '#000',
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'text-wrap': 'wrap',
                        'text-max-width': '200px',
                        'width': 'label',
                        'height': 'label',
                        'padding': '16px',
                        'shape': 'round-rectangle',
                        'border-width': 2,
                        'border-color': '#333',
                        'font-size': '14px',
                        'font-weight': 'bold'
                    }
                },
                {
                    selector: ':parent',
                    style: {
                        'text-valign': 'top',
                        'text-halign': 'center',
                        'background-opacity': 0.1,
                        'border-style': 'dashed',
                        'border-width': 2,
                        'border-color': '#999',
                        'padding': '40px' 
                    }
                },
                {
                    selector: 'node:selected',
                    style: {
                        'border-width': 4,
                        'border-color': '#007bff'
                    }
                },
                {
                    selector: 'edge',
                    style: {
                        'width': 3,
                        'line-color': '#999',
                        'target-arrow-color': '#999',
                        'target-arrow-shape': 'triangle',
                        'arrow-scale': 1.2,
                        'curve-style': 'bezier',
                        'label': 'data(label)',
                        'font-size': '12px',
                        'text-rotation': 'autorotate',
                        'text-background-color': '#ffffff',
                        'text-background-opacity': 0.9,
                        'text-background-padding': '3px',
                        'text-margin-y': -8
                    }
                },
                {
                    selector: '.faded',
                    style: {
                        'opacity': 0.1,
                        'text-opacity': 0.1,
                        'events': 'no'
                    }
                },
                {
                    selector: '.inactive-edge',
                    style: {
                        'opacity': 0.05,
                        'line-style': 'dashed'
                    }
                }
            ],
            layout: {
                name: 'breadthfirst', 
                directed: true,
                padding: 50,
                spacingFactor: 1.2,
                avoidOverlap: true,
                nodeDimensionsIncludeLabels: true
            }
        });

        window.cy.on('tap', 'node', function(evt){
            if (evt.target.hasClass('faded')) return;
            var link = evt.target.data('link');
            if(link){
                console.log("Navigating to:", link);
                window.location.href = link;
            }
        });

        // Context Menu (Right Click)
        window.cy.on('cxttap', 'node, edge', function(evt){
            var target = evt.target;
            var data = target.data();
            var type = target.isNode() ? 'Node' : 'Edge';
            
            if (data) {
                var content = '<div style="margin-bottom:5px; border-bottom:1px solid #555; padding-bottom:3px; font-weight:bold; color:#00d1b2;">' + type + ' Raw Data</div>';
                
                if (!target.isNode()) {
                    var sLabel = target.source().data('label') || target.source().id();
                    var tLabel = target.target().data('label') || target.target().id();
                    content += '<div style="margin-bottom:5px; font-size:0.9em;"><span style="color:#aaa;">From:</span> ' + sLabel + '</div>';
                    content += '<div style="margin-bottom:8px; font-size:0.9em;"><span style="color:#aaa;">To:</span> ' + tLabel + '</div>';
                }

                function formatValue(val) {
                    if (val === null) return 'null';
                    
                    if (Array.isArray(val) || (typeof val === 'object')) {
                        var isArray = Array.isArray(val);
                        var keys = Object.keys(val);
                        if (keys.length === 0) return isArray ? '[]' : '{}';
                        
                        var label = isArray ? 'Array [' + val.length + ']' : 'Object';
                        var html = '<div class="tooltip-expander" style="cursor:pointer; color:#00d1b2; font-weight:bold; display:inline-block;">[+] ' + label + '</div>';
                        html += '<div class="tooltip-nested" style="display:none; margin-left:10px; border-left:1px solid #555; padding-left:5px;">';
                        
                        for (var k in val) {
                            if (val.hasOwnProperty(k)) {
                                html += '<div><span style="color:#aaa;">' + k + ':</span> ' + formatValue(val[k]) + '</div>';
                            }
                        }
                        html += '</div>';
                        return html;
                    }
                    return val;
                }

                for (var key in data) {
                    if (data.hasOwnProperty(key)) {
                        var val = data[key];
                        if (val === null) continue;
                        if (target.isNode() && (key === 'bg' || key === 'link')) continue;
                        if (!target.isNode() && (key === 'source' || key === 'target')) continue;
                        
                        content += '<div style="margin-top:2px;"><strong style="color:#aaa;">' + key + ':</strong> ' + formatValue(val) + '</div>';
                    }
                }
                
                var $tooltip = $('#node_tooltip');
                $tooltip.html(content);
                
                // Position logic
                var e = evt.originalEvent;
                var x = e.clientX + 10;
                var y = e.clientY + 10;
                
                // Boundary check (simple)
                if (x + 300 > $(window).width()) x -= 310;
                if (y + 200 > $(window).height()) y -= 210;

                $tooltip.css({
                    top: y + 'px',
                    left: x + 'px'
                }).fadeIn(200);
            }
        });

        // Hide tooltip on click anywhere
        window.cy.on('tap pan zoom', function(){
            $('#node_tooltip').fadeOut(100);
        });
    }

    // 4. FILTER LOGIC
    function populateDidFilter(graphData) {
        var $list = $('#filter_list');
        $list.empty();
        
        var dids = graphData.filter(function(el) {
            return el.data && el.data.type === 'ingress';
        });
        
        dids.sort(function(a, b) {
            var la = a.data.label || '';
            var lb = b.data.label || '';
            return la.localeCompare(lb);
        });

        if (dids.length === 0) {
            $list.html('<div style="padding:5px; color:#999;">No Phone Numbers found.</div>');
            return;
        }

        dids.forEach(function(did) {
            var id = did.data.id;
            var label = did.data.label.replace('Phone Number: ', '');
            
            var row = $('<div class="filter-row" style="padding: 2px 0;"></div>');
            var lbl = $('<label style="font-weight: normal; cursor: pointer; display: block; margin: 0; user-select: none;"></label>');
            var chk = $('<input type="checkbox" class="did-checkbox" checked value="' + id + '" style="margin-right: 5px;">');
            
            lbl.append(chk).append(document.createTextNode(label));
            row.append(lbl);
            $list.append(row);
        });
        
        $('#cb_select_all').prop('checked', true);
        $('#filter_count').text('');
        $('#filter_search').val('');
    }

    function applyFilter() {
        if (!window.cy) return;

        var allChecked = $('#cb_select_all').is(':checked');
        var checkedBoxes = $('#filter_list .did-checkbox:checked');
        var totalBoxes = $('#filter_list .did-checkbox').length;

        var visibleElements;

        window.cy.batch(function() {
            var elements = window.cy.elements();

            // Reset
            elements.removeClass('faded');

            if (allChecked || checkedBoxes.length === totalBoxes) {
                $('#filter_count').text('');
                // Fit All
                return;
            }

            if (checkedBoxes.length === 0) {
                elements.addClass('faded');
                $('#filter_count').text('0');
                return;
            }

            $('#filter_count').text(checkedBoxes.length);
            elements.addClass('faded');

            var selectedIds = [];
            checkedBoxes.each(function() {
                selectedIds.push('#' + $(this).val());
            });
            var selector = selectedIds.join(',');

            var roots = window.cy.nodes(selector);
            var path = roots.successors().union(roots);

            path.removeClass('faded');
            visibleElements = path;
        });

        // Auto-Fit to visible elements
        if (visibleElements && visibleElements.length > 0) {
            window.cy.animate({
                fit: {
                    eles: visibleElements,
                    padding: 50
                },
                duration: 500
            });
        }
    }

    // --- MAIN INJECTION LOGIC ---
    function initRouteGraph() {
        var isDebug = localStorage.getItem("ROUTE_GRAPH_DEBUG") === "true";

        if (isDebug) {
            console.log("Route Graph Debug Mode: ON");
        }

        if ($('#tab_route_graph').length > 0) return;

        var $phoneTab = $('.nav-tabs a:contains("Phone Numbers")');
        var $nativePanel = $('.inventory-panel-main');

        if ($phoneTab.length > 0 && $nativePanel.length > 0) {

            var elementsToHide = '.inventory-panel-main, .alert:not(.alert-info), .action-container-left, .action-container-right';
            var $navContainer = $phoneTab.closest('ul');
            var $parentContainer = $nativePanel.parent();

            $navContainer.append(
                '<li id="tab_route_graph">' +
                    '<a href="javascript:void(0);" style="cursor: pointer;">Route Graph</a>' +
                '</li>'
            );

            var btnStyle = 'margin-right: 5px;';

            // Filter Popover HTML
            var filterHtml = 
                '<div style="display: inline-block; position: relative; margin-right: 5px;">' +
                    '<button id="btn_toggle_filter" class="btn btn-sm btn-default"><i class="fa fa-filter"></i> Phone Number Filter <span id="filter_count" class="badge"></span></button>' +
                    '<div id="filter_popover" style="display: none; position: absolute; top: 100%; left: 0; z-index: 1000; background: #fff; border: 1px solid #ccc; padding: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); min-width: 250px; max-height: 400px; overflow-y: auto;">' +
                        '<div style="margin-bottom: 8px;">' +
                            '<input type="text" id="filter_search" class="form-control input-sm" placeholder="Search Phone Numbers...">' +
                        '</div>' +
                        '<div style="border-bottom: 1px solid #eee; padding-bottom: 5px; margin-bottom: 5px;">' +
                            '<label style="font-weight: bold; cursor: pointer; display: block; margin: 0;"><input type="checkbox" id="cb_select_all" checked style="margin-right: 5px;"> All Phone Numbers</label>' +
                        '</div>' +
                        '<div id="filter_list"></div>' +
                    '</div>' +
                '</div>';

            // Time Simulator Popover HTML
            var timeSimHtml = 
                '<div style="display: inline-block; position: relative; margin-right: 5px;">' +
                    '<button id="btn_toggle_time" class="btn btn-sm btn-default"><i class="fa fa-clock-o"></i> Time Simulator <span id="time_sim_badge" class="badge" style="display:none">ON</span></button>' +
                    '<div id="time_popover" style="display: none; position: absolute; top: 100%; left: 0; z-index: 1000; background: #fff; border: 1px solid #ccc; padding: 15px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); min-width: 280px;">' +
                        '<div class="form-group">' +
                            '<label>Simulate Date & Time</label>' +
                            '<input type="datetime-local" id="sim_datetime" class="form-control input-sm">' +
                        '</div>' +
                        '<div style="margin-top: 10px; text-align: right;">' +
                            '<button id="btn_sim_now" class="btn btn-xs btn-link">Set to Now</button>' + 
                            '<button id="btn_sim_clear" class="btn btn-sm btn-default">Clear</button>' +
                            '<button id="btn_sim_apply" class="btn btn-sm btn-primary">Apply</button>' +
                        '</div>' +
                    '</div>' +
                '</div>';

            var tooltipHtml = '<div id="node_tooltip" style="display:none; position:fixed; z-index:9999; background:rgba(0,0,0,0.9); color:#fff; padding:10px; border-radius:4px; font-size:12px; max-width:400px; max-height:80vh; overflow-y:auto; box-shadow: 2px 2px 5px rgba(0,0,0,0.3);"></div>';

            var newContentHTML =
                '<div id="content_route_graph" style="display:none; padding: 20px; background: #fff; height: 100%; position: relative;">' +
                    '<h3>Route Graph</h3>' +
                    '<div id="graph_toolbar" style="margin-bottom: 10px;">' +
                        filterHtml +
                        timeSimHtml +
                        '<button id="btn_fullscreen" class="btn btn-sm btn-default" style="' + btnStyle + '"><i class="fa fa-arrows-alt"></i> Full Screen</button>' +
                        '<button id="btn_fit" class="btn btn-sm btn-default" style="' + btnStyle + '"><i class="fa fa-compress"></i> Fit</button>' +
                        '<button id="btn_zoom_in" class="btn btn-sm btn-default" style="' + btnStyle + '"><i class="fa fa-plus"></i></button>' +
                        '<button id="btn_zoom_out" class="btn btn-sm btn-default" style="' + btnStyle + '"><i class="fa fa-minus"></i></button>' +
                        '<button id="btn_export_png" class="btn btn-sm btn-default" style="' + btnStyle + '"><i class="fa fa-file-image-o"></i> PNG</button>' +
                        '<button id="btn_export_drawio" class="btn btn-sm btn-default"><i class="fa fa-download"></i> Export Draw.io</button>' +
                    '</div>' +
                    '<div id="cy_container" style="width: 100%; height: 600px; border: 1px solid #ddd; background: #f9f9f9;"></div>' +
                    tooltipHtml +
                    '<p style="font-size: 0.8em; color: #666; margin-top: 5px;">Click on a node to view details in the portal. Right-click for more info. Use scroll wheel to zoom.</p>' +
                '</div>';

            $parentContainer.append(newContentHTML);

            // --- EVENT HANDLERS ---

            // Tooltip Expander Handler
            $(document).off('click', '.tooltip-expander').on('click', '.tooltip-expander', function(e) {
                e.stopPropagation();
                var $btn = $(this);
                var $content = $btn.next('.tooltip-nested');
                $content.toggle();
                $btn.text($content.is(':visible') ? '[-] Collapse' : '[+] Expand');
            });

            // Time Simulator Handlers
            $('#btn_toggle_time').on('click', function(e) {
                e.stopPropagation();
                $('#time_popover').toggle();
                $('#filter_popover').hide();
                
                // Set default to now if empty
                if (!$('#sim_datetime').val()) {
                     $('#btn_sim_now').click();
                }
            });

            $('#btn_sim_now').on('click', function() {
                var now = new Date();
                // Format for datetime-local: YYYY-MM-DDTHH:MM
                now.setMinutes(now.getMinutes() - now.getTimezoneOffset()); // Adjust to local string
                var str = now.toISOString().slice(0, 16);
                $('#sim_datetime').val(str);
            });

            $('#btn_sim_clear').on('click', function() {
                $('#time_sim_badge').hide();
                if (window.cy) {
                    window.cy.edges().removeClass('faded inactive-edge');
                    window.cy.nodes().removeClass('faded');
                }
                applyFilter(); 
                $('#time_popover').hide();
            });

            $('#btn_sim_apply').on('click', function() {
                var val = $('#sim_datetime').val();
                if (!val) return;
                
                var dateObj = new Date(val);
                $('#time_sim_badge').show();
                applyTimeSimulation(dateObj);
                $('#time_popover').hide();
            });

            function applyTimeSimulation(simDate) {
                if (!window.cy) return;
                
                // Extract components
                var simDay = simDate.getDay(); // 0 (Sun) - 6 (Sat)
                // Normalize 0(Sun) to 7? NetSapiens usage varies. 
                // Based on "Monday=1", usually 0(Sun) maps to 7 or 0.
                // Let's assume standard ISO: 1=Mon ... 7=Sun.
                var nsDay = (simDay === 0) ? 7 : simDay; 
                
                // HH:MM
                var hh = String(simDate.getHours()).padStart(2, '0');
                var mm = String(simDate.getMinutes()).padStart(2, '0');
                var simTimeStr = hh + ':' + mm;

                // YYYY-MM-DD
                var yyyy = simDate.getFullYear();
                var mon = String(simDate.getMonth() + 1).padStart(2, '0');
                var dd = String(simDate.getDate()).padStart(2, '0');
                var simDateStr = yyyy + '-' + mon + '-' + dd;

                function isRangeMatch(range) {
                    // 1. Check Specific Date (Holidays)
                    var rStart = range['start-date'];
                    var rEnd = range['end-date'];
                    
                    var isSpecific = (rStart && rStart !== 'now' && rStart !== 'never');
                    
                    if (isSpecific) {
                        // String compare YYYY-MM-DD
                        if (simDateStr < rStart || simDateStr > rEnd) return false;
                    }
                    
                    // 2. Check Day of Week (Recurrence)
                    if (!isSpecific) {
                        var rDay = range['day-of-week-number'];
                        if (rDay && rDay !== '*' && rDay != nsDay) {
                             return false;
                        }
                    }
                    
                    // 3. Check Time
                    var start = range['start-time'];
                    var end = range['end-time'];
                    
                    if (start && end) {
                        return simTimeStr >= start && simTimeStr <= end;
                    }
                    
                    return true;
                }

                window.cy.batch(function() {
                    var cy = window.cy;
                    var nodes = cy.nodes();
                    
                    cy.edges().removeClass('inactive-edge');

                    nodes.each(function(node) {
                        var edges = node.outgoers('edge');
                        if (edges.length === 0) return;

                        // 1. Group by Priority
                        var groups = {};
                        var priorities = [];
                        
                        edges.each(function(edge) {
                            var p = edge.data('priority');
                            if (p === undefined || p === null) p = 9999;
                            if (!groups[p]) {
                                groups[p] = [];
                                priorities.push(p);
                            }
                            groups[p].push(edge);
                        });
                        
                        priorities.sort(function(a, b) { return a - b; });

                        // 2. Find Active Group
                        var activeFound = false;
                        var activeEdges = [];

                        for (var i = 0; i < priorities.length; i++) {
                            var p = priorities[i];
                            var groupEdges = groups[p];
                            var groupMatch = false;
                            
                            var firstEdge = groupEdges[0];
                            var ranges = firstEdge.data('time_range_data');
                            
                            if (!ranges || ranges.length === 0) {
                                groupMatch = true;
                            } else {
                                for (var r = 0; r < ranges.length; r++) {
                                    if (isRangeMatch(ranges[r])) {
                                        groupMatch = true;
                                        break;
                                    }
                                }
                            }
                            
                            if (groupMatch) {
                                activeFound = true;
                                activeEdges = groupEdges;
                                break; 
                            }
                        }

                        // 3. Mark Inactive
                        edges.each(function(edge) {
                            var isActive = false;
                            if (activeFound) {
                                for(var k=0; k<activeEdges.length; k++) {
                                    if (activeEdges[k] === edge) isActive = true;
                                }
                            }
                            
                            if (!isActive) {
                                edge.addClass('inactive-edge');
                            }
                        });
                    });
                });
            }

            // Filter Toggle
            $('#btn_toggle_filter').on('click', function(e) {
                e.stopPropagation();
                $('#filter_popover').toggle();
                setTimeout(function(){ $('#filter_search').focus(); }, 100);
            });

            $(document).on('click', function(e) {
                if (!$(e.target).closest('#filter_popover, #btn_toggle_filter').length) {
                    $('#filter_popover').hide();
                }
            });

            // Search Filter Logic
            $('#filter_search').on('keyup', function() {
                var val = $(this).val().toLowerCase();
                $('#filter_list .filter-row').each(function() {
                    var text = $(this).text().toLowerCase();
                    $(this).toggle(text.indexOf(val) > -1);
                });
            });

            $('#cb_select_all').on('change', function() {
                var isChecked = $(this).is(':checked');
                var $visibleCheckboxes = $('#filter_list .filter-row:visible .did-checkbox');
                $visibleCheckboxes.prop('checked', isChecked);
                
                if (!isChecked) {
                     $('#filter_list .did-checkbox').prop('checked', false);
                } else if ($('#filter_search').val() === '') {
                     $('#filter_list .did-checkbox').prop('checked', true);
                }
                
                applyFilter();
            });

            $('#filter_list').on('change', '.did-checkbox', function() {
                var total = $('#filter_list .did-checkbox').length;
                var checked = $('#filter_list .did-checkbox:checked').length;
                $('#cb_select_all').prop('checked', total === checked && total > 0);
                
                applyFilter();
            });

            $('#btn_export_png').on('click', function() {
                if(!window.cy) return;
                var png64 = window.cy.png({ output: 'base64uri', full: true, scale: 2, bg: '#ffffff' });
                downloadFile(png64, 'call_flow.png');
            });

            $('#btn_export_drawio').on('click', function() {
                if(!window.cy) return;
                var xml = generateDrawIoXml(window.cy);
                var blob = new Blob([xml], {type: 'text/xml'});
                var url = window.URL.createObjectURL(blob);
                downloadFile(url, 'call_flow.drawio');
                window.URL.revokeObjectURL(url);
            });

            function downloadFile(href, name) {
                var a = document.createElement('a');
                a.href = href;
                a.download = name;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            }

            function generateDrawIoXml(cy) {
                var nodes = cy.nodes();
                var edges = cy.edges();
                
                var xml = '<mxfile host="app.diagrams.net" modified="' + new Date().toISOString() + '" agent="RouteGraph" etag="1" version="14.6.13" type="device">';
                xml += '  <diagram id="CallFlow" name="Page-1">';
                xml += '    <mxGraphModel dx="1422" dy="794" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="850" pageHeight="1100" math="0" shadow="0">';
                xml += '      <root>';
                xml += '        <mxCell id="0" />';
                xml += '        <mxCell id="1" parent="0" />';
                
                nodes.each(function(node) {
                    var id = node.id();
                    var label = node.data('label') || id;
                    var pos = node.position();
                    var bg = node.data('bg') || '#ffffff';
                    var width = node.width();
                    var height = node.height();
                    
                    label = label.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
                    
                    var style = 'rounded=1;whiteSpace=wrap;html=1;fillColor=' + bg + ';strokeColor=#333333;fontColor=#000000;fontStyle=1;';
                    if (node.isParent()) {
                        style += 'verticalAlign=top;dashed=1;fillColor=none;strokeColor=#666666;opacity=50;';
                        width += 40; height += 40;
                    }
                    
                    xml += '        <mxCell id="' + id + '" value="' + label + '" style="' + style + '" vertex="1" parent="1">';
                    xml += '          <mxGeometry x="' + pos.x + '" y="' + pos.y + '" width="' + width + '" height="' + height + '" as="geometry" />';
                    xml += '        </mxCell>';
                });
                
                edges.each(function(edge) {
                    var id = edge.id();
                    var source = edge.source().id();
                    var target = edge.target().id();
                    var label = edge.data('label') || '';
                    label = label.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
                    
                    var style = 'edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;entryX=0;entryY=0.5;entryDx=0;entryDy=0;strokeColor=#333333;strokeWidth=2;';
                    
                    xml += '        <mxCell id="' + id + '" value="' + label + '" style="' + style + '" edge="1" parent="1" source="' + source + '" target="' + target + '">';
                    xml += '          <mxGeometry relative="1" as="geometry" />';
                    xml += '        </mxCell>';
                });
                
                xml += '      </root>';
                xml += '    </mxGraphModel>';
                xml += '  </diagram>';
                xml += '</mxfile>';
                return xml;
            }

            $('#btn_fullscreen').on('click', function() {
                var elem = document.getElementById("content_route_graph");
                if (!document.fullscreenElement) {
                    elem.requestFullscreen().catch(err => console.log(err));
                    $('#cy_container').css('height', '90vh');
                } else {
                    document.exitFullscreen();
                    $('#cy_container').css('height', '600px');
                }
            });
            
            document.addEventListener('fullscreenchange', (event) => {
                if (!document.fullscreenElement) {
                     $('#cy_container').css('height', '600px');
                     if(window.cy) window.cy.resize();
                } else {
                     if(window.cy) window.cy.resize();
                }
            });

            $('#btn_fit').on('click', function() {
                if(window.cy) window.cy.fit(30);
            });

            $('#btn_zoom_in').on('click', function() {
                if(window.cy) window.cy.zoom(window.cy.zoom() * 1.2);
            });

            $('#btn_zoom_out').on('click', function() {
                if(window.cy) window.cy.zoom(window.cy.zoom() * 0.8);
            });

            $('#tab_route_graph a').on('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                $navContainer.find('li').removeClass('active nav-link-current');
                $('#tab_route_graph').addClass('active');
                $(elementsToHide).hide();
                $('#content_route_graph').show();
                ensureCytoscapeLoaded(function() { loadGraphData(); });
            });

            $navContainer.find('li').not('#tab_route_graph').find('a').on('click', function() {
                $('#tab_route_graph').removeClass('active');
                $('#content_route_graph').hide();
                $(elementsToHide).css('display', '');
            });
        }
    }

    initRouteGraph();
    var observer = new MutationObserver(function(mutations) {
        initRouteGraph();
    });
    observer.observe(document.body, { childList: true, subtree: true });

})();
