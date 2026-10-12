-- Insertamos usuarios en su tabla
INSERT INTO usuarios (username, password_hash, pais, saldo) VALUES 
('alba123', '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 'Bélgica', 150.00),
('martam', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', 'Italia', 50.00),
('diego', '65e84be33532fb784c48129675f9eff3a682b27168c0ea744b2cf58ee02337c5', 'España', 10.50);

-- Insertamos películas en el catálogo
INSERT INTO peliculas (titulo, genero, año, precio, stock) VALUES
('El El Señor de los Anillos: El Retorno del Rey', 'Fantasía', 2003, 9.99, 50),
('Matrix', 'Ciencia Ficción', 1999, 15.00, 30),
('Pulp fiction', 'Crimen', 1994, 8.50, 15),
('Shrek', 'Animación', 2001, 6.99, 20),
('Interstellar', 'Ciencia Ficción', 2014, 10.50, 40);

-- Insertamos algunas valoraciones
INSERT INTO valoraciones (usuario_id, pelicula_id, puntuacion) VALUES
(1, 1, 10.0),
(2, 1, 9.5),
(1, 2, 8.0),
(3, 4, 9.0);