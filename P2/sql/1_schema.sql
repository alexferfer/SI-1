-- Creamos todas las tablas necesarias con sus columnas y condiciones.

CREATE TABLE usuarios
(
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) UNIQUE NOT NULL,
    pais VARCHAR(100) NOT NULL, 
    saldo NUMERIC(100,2) DEFAULT 0.0
);

CREATE TABLE peliculas
(
    id SERIAL PRIMARY KEY,
    titulo VARCHAR(200) NOT NULL,
    genero VARCHAR(200) DEFAULT 'General',
    año INTEGER NOT NULL,
    precio NUMERIC(100, 2) NOT NULL,
    stock INTEGER DEFAULT 10
);

CREATE TABLE pedidos
(
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    estado VARCHAR(20) DEFAULT 'CARRITO',
    fecha_pago TIMESTAMP
);

CREATE TABLE pedido_items
(
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    pelicula_id INTEGER NOT NULL REFERENCES peliculas(id) ON DELETE CASCADE,
    cantidad INTEGER DEFAULT 1,
    precio_unitario NUMERIC(100, 2) NOT NULL
);

CREATE TABLE valoraciones
(
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    pelicula_id INTEGER NOT NULL REFERENCES peliculas(id) ON DELETE CASCADE,
    puntuacion NUMERIC(4, 2) CHECK (puntuacion <= 10 AND puntuacion >= 0),
    UNIQUE(usuario_id, pelicula_id)
);

-- Creamos los triggers necesarios para la práctica que serán ejecutados según su condición


-- Trigger encargado de actualizar el stock
CREATE OR REPLACE FUNCTION tg_actualizar_stock()
RETURNS TRIGGER AS $$

BEGIN 

    IF TG_OP = 'INSERT' THEN 

        UPDATE peliculas SET stock = stock - NEW.cantidad WHERE id = NEW.pelicula_id;
        RETURN NEW;

    ELSIF TG_OP = 'DELETE' THEN

        UPDATE peliculas SET stock = stock + OLD.cantidad WHERE id = OLD.pelicula_id;
        RETURN OLD;
    
    END IF;
    RETURN NULL;

END;

$$ LANGUAGE plpgsql;


-- Trigger encargado actualizar el stock cada vez que se actualice la tabla de pedido_items
CREATE TRIGGER tgr_actualizar_stock
AFTER INSERT OR DELETE ON pedido_items
FOR EACH ROW EXECUTE FUNCTION tg_actualizar_stock();

-- Trigger encargado de descontar el saldo al pagar en el carrito

CREATE OR REPLACE FUNCTION tg_pagar_carrito()
RETURNS TRIGGER AS $$
DECLARE

    coste_total NUMERIC;

BEGIN

    IF NEW.estado = 'PAGADO' AND OLD.estado = 'CARRITO' THEN

        SELECT COALESCE(SUM(cantidad * precio_unitario), 0) INTO coste_total
        FROM pedido_items
        WHERE pedido_id = NEW.id;

        UPDATE usuarios SET saldo = saldo - coste_total WHERE id = NEW.usuario_id;

    END IF;
    RETURN NEW;

END;

$$ LANGUAGE plpgsql;


-- Trigger encargado de cobrar un producto al cliente cada vez que se actualice la tabla de pedidos
CREATE TRIGGER trg_pagar_carrito
AFTER UPDATE ON pedidos
FOR EACH ROW EXECUTE FUNCTION tg_pagar_carrito();


-- Creamos el paquete encargado de calcular la nota media de la película

CREATE OR REPLACE FUNCTION sp_calcular_nota_media(p_pelicula_id INTEGER)
RETURNS NUMERIC AS $$

DECLARE 

    nota_media NUMERIC(4, 2);

BEGIN 

    SELECT COALESCE(AVG(puntuacion), 0) INTO nota_media
    FROM valoraciones
    WHERE pelicula_id = p_pelicula_id;

    RETURN nota_media;

END;

$$ LANGUAGE plpgsql;



