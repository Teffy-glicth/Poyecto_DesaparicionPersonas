window.Etapa5 = (function () {
    const PALETA = {
        "Hombre": "#4a5d6e",
        "Mujer": "#7a1f1f",
        "Sur": "#9c7a2e",
        "Resto": "#4a5d6e",
        "Sin resolver": "#7a1f1f",
        "Desaparecido": "#7a1f1f",
        "Resuelto": "#3f6b4f",
        "Aparecido con vida": "#3f6b4f",
        "Aparecido sin vida": "#6b6558",
        "Medicina Legal (SIRDEC)": "#4a5d6e",
        "SIEVCAC (CNMH)": "#9c7a2e",
        "Antes (2007-2016)": "#6a4c93",
        "Despues (2017-2025)": "#3f6b4f",
        "Sin informacion": "#b9b2a0",
        "Sin Informacion": "#b9b2a0",
    };

    function colorDe(etiqueta, indice) {
        if (PALETA[etiqueta]) return PALETA[etiqueta];
        const paletaExtra = ["#7a1f1f", "#4a5d6e", "#9c7a2e", "#3f6b4f", "#6a4c93", "#b9b2a0"];
        return paletaExtra[indice % paletaExtra.length];
    }

    function endpointVista() {
        return document.getElementById("etapa5-vista").dataset.apiEndpoint;
    }

    function leerFiltros(selector) {
        selector = selector || "#etapa5-filtros";
        const params = new URLSearchParams();
        const contenedor = document.querySelector(selector);
        if (!contenedor) return params;
        contenedor.querySelectorAll("[data-filtro]").forEach(function (el) {
            if (el.value) params.set(el.dataset.filtro, el.value);
        });
        return params;
    }

    async function consultar(paramsExtra) {
        const params = leerFiltros();
        if (paramsExtra) {
            Object.entries(paramsExtra).forEach(function ([clave, valor]) {
                if (valor === null || valor === undefined || valor === "") {
                    params.delete(clave);
                } else {
                    params.set(clave, valor);
                }
            });
        }
        const url = "/api/etapa5/" + endpointVista() + "?" + params.toString();
        const resp = await fetch(url);
        if (!resp.ok) {
            throw new Error("Error " + resp.status + " al consultar " + url);
        }
        return resp.json();
    }

    function formatoNumero(valor) {
        if (valor === null || valor === undefined) return "—";
        return Number(valor).toLocaleString("es-CO");
    }

    function pintarIndicadores(indicadores) {
        const cont = document.getElementById("etapa5-indicadores");
        cont.innerHTML = indicadores.map(function (ind) {
            const sufijo = ind.unidad === "%" ? " %" : (ind.unidad === "pp" ? " pp" : "");
            const nota = ind.denominador != null
                ? '<p class="nota">sobre ' + formatoNumero(ind.denominador) + " personas</p>"
                : "";
            return (
                '<div class="etapa5-indicador-card">' +
                '<p class="etapa5-indicador-valor">' + ind.valor + sufijo + "</p>" +
                '<p class="etapa5-indicador-etiqueta">' + ind.etiqueta + "</p>" +
                nota +
                "</div>"
            );
        }).join("");
    }

    function destruirChart(id) {
        const existente = Chart.getChart(id);
        if (existente) existente.destroy();
    }

    
    function pintarMatriz(matriz, contenedorId, opciones) {
        contenedorId = contenedorId || "etapa5-matriz";
        opciones = opciones || {};
        const calor = opciones.calor !== false;
        const cont = document.getElementById(contenedorId);
        const totales = matriz.totales_fila || matriz.filas.map(function (_, i) {
            return matriz.celdas[i].reduce(function (a, b) { return a + (b || 0); }, 0);
        });
        const claseTabla = "etapa5-tabla-matriz" + (opciones.alClicFila ? " etapa5-matriz-clic" : "");
        let html = '<div class="tabla-scroll"><table class="' + claseTabla + '"><thead><tr><th></th>';
        matriz.columnas.forEach(function (c) { html += "<th>" + c + "</th>"; });
        html += "<th>Total fila</th></tr></thead><tbody>";
        matriz.filas.forEach(function (fila, i) {
            html += '<tr data-fila="' + String(fila).replace(/"/g, "&quot;") + '"><th>' + fila + "</th>";
            const total = totales[i] || 0;
            matriz.celdas[i].forEach(function (valor) {
                const pctNum = total ? (valor || 0) * 100 / total : 0;
                const estilo = calor
                    ? ' style="background: rgba(122, 31, 31, ' + (pctNum / 100 * 0.35).toFixed(3) + ')"'
                    : "";
                html += "<td" + estilo + ">" + formatoNumero(valor || 0) +
                    ' <span class="nota">(' + pctNum.toFixed(1) + " %)</span></td>";
            });
            html += "<td><strong>" + formatoNumero(total) + "</strong></td></tr>";
        });
        html += "</tbody></table></div>";
        html += '<p class="nota">Cada % usa como denominador el total de su fila. Un color más intenso indica un % mayor dentro de la fila.</p>';
        cont.innerHTML = html;
        if (opciones.alClicFila) {
            cont.querySelectorAll("tbody tr").forEach(function (tr) {
                tr.addEventListener("click", function () { opciones.alClicFila(tr.dataset.fila); });
            });
        }
    }

    function mostrarSeleccionActiva(filtros, extra) {
        const el = document.getElementById("etapa5-seleccion");
        const partes = Object.entries(filtros || {}).filter(function ([, v]) { return v; }).map(function ([k, v]) {
            return k + " = " + (Array.isArray(v) ? v.join(" / ") : v);
        });
               if (extra) partes.push(extra);
        el.innerHTML = '<span class="etapa5-seleccion-titulo">Selección activa:</span> ' + (partes.length
            ? partes.map(function (p) { return '<span class="etapa5-chip">' + p + "</span>"; }).join(" ")
            : '<span class="etapa5-chip etapa5-chip-vacio">ninguna (vista completa, sin filtros)</span>');
    }

    return {
        leerFiltros: leerFiltros,
        consultar: consultar,
        pintarIndicadores: pintarIndicadores,
        pintarMatriz: pintarMatriz,
        mostrarSeleccionActiva: mostrarSeleccionActiva,
        destruirChart: destruirChart,
        colorDe: colorDe,
        formatoNumero: formatoNumero,
    };
})();
