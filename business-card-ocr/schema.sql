CREATE DATABASE IF NOT EXISTS business_cards_db;
USE business_cards_db;

CREATE TABLE `business_cards` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `card_id` VARCHAR(50) NOT NULL,
  `side` ENUM('front','back') NOT NULL,
  `raw_text` TEXT NOT NULL,
  `image_path` VARCHAR(255) NOT NULL,
  `created_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_card_side` (`card_id`,`side`) -- ensures no duplicate front/back for same card_id
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
