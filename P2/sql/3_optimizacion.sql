-- Query a optimizar

EXPLAIN ANALYZE
SELECT 
    o.id AS pedido_id, o.fecha_pago, u.username, u.pais,
    p.titulo, oi.cantidad, oi.precio_unitario,
    (oi.cantidad * oi.precio_unitario) AS subtotal
FROM pedidos o
JOIN usuarios u ON o.usuario_id = u.id
JOIN pedido_items oi ON oi.pedido_id = o.id
JOIN peliculas p ON oi.pelicula_id = p.id
WHERE o.estado = 'PAGADO'
  AND EXTRACT(YEAR FROM o.fecha_pago) = 2020
  AND u.pais = 'España';

-- Probamos primero creando índices simples para mejorar el rendimiento de la consulta

CREATE INDEX idx_usuarios_pais ON usuarios(pais);
CREATE INDEX idx_pedidos_fecha ON pedidos (EXTRACT(YEAR FROM fecha_pago));

-- Comparamos el rendimiento anterior si en vez de un índice simple usamos un índice compuesto agrupando a la vez 
-- por el estado del pedido y el año del mismo

DROP INDEX idx_pedidos_fecha;

CREATE INDEX idx_pedidos_compuesto ON pedidos (estado, EXTRACT(YEAR FROM fecha_pago));

-- Comparamos el rendimiento de los anteriores con un índice parcial filtrado únicamente aquellos cuyo estado sea pagado

DROP INDEX idx_pedidos_compuesto;
CREATE INDEX idx_pedidos_parcial ON pedidos (EXTRACT(YEAR FROM fecha_pago)) WHERE estado = 'PAGADO';