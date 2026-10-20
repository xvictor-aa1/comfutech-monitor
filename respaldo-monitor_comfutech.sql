-- --------------------------------------------------------
-- Host:                         192.168.0.248
-- Versión del servidor:         13.0.2-MariaDB - MariaDB Server
-- SO del servidor:              Win64
-- HeidiSQL Versión:             12.21.0.7344
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8 */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;


-- Volcando estructura de base de datos para monitoreo_red
CREATE DATABASE IF NOT EXISTS `monitoreo_red` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci */;
USE `monitoreo_red`;

-- Volcando estructura para tabla monitoreo_red.alert_rules
CREATE TABLE IF NOT EXISTS `alert_rules` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  `description` longtext NOT NULL,
  `metric` varchar(50) NOT NULL,
  `operator` varchar(10) NOT NULL,
  `threshold` decimal(15,4) NOT NULL,
  `duration_sec` int(10) unsigned NOT NULL CHECK (`duration_sec` >= 0),
  `severity` varchar(20) NOT NULL,
  `custom_message` longtext NOT NULL,
  `telegram_enabled` tinyint(1) NOT NULL,
  `telegram_cooldown_sec` int(10) unsigned NOT NULL CHECK (`telegram_cooldown_sec` >= 0),
  `enabled` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `created_by_id` int(11) DEFAULT NULL,
  `device_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `alert_rules_created_by_id_c251154b_fk_auth_user_id` (`created_by_id`),
  KEY `alert_rules_device_id_7c6ee67d_fk_devices_id` (`device_id`),
  CONSTRAINT `alert_rules_created_by_id_c251154b_fk_auth_user_id` FOREIGN KEY (`created_by_id`) REFERENCES `auth_user` (`id`),
  CONSTRAINT `alert_rules_device_id_7c6ee67d_fk_devices_id` FOREIGN KEY (`device_id`) REFERENCES `devices` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla monitoreo_red.alert_rules: ~1 rows (aproximadamente)
REPLACE INTO `alert_rules` (`id`, `name`, `description`, `metric`, `operator`, `threshold`, `duration_sec`, `severity`, `custom_message`, `telegram_enabled`, `telegram_cooldown_sec`, `enabled`, `created_at`, `updated_at`, `created_by_id`, `device_id`) VALUES
	(1, 'RB Güigüe caída del dispositivo', '', 'device_down', 'eq', 0.0000, 300, 'critical', 'Servidor {device} desconectado', 1, 600, 1, '2026-10-06 00:58:41.272906', '2026-10-07 02:18:38.069159', 1, 1);

-- Volcando estructura para tabla monitoreo_red.alerts
CREATE TABLE IF NOT EXISTS `alerts` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `alert_type` varchar(50) NOT NULL,
  `severity` varchar(20) NOT NULL,
  `message` longtext NOT NULL,
  `value_observed` decimal(20,4) DEFAULT NULL,
  `threshold_value` decimal(20,4) DEFAULT NULL,
  `status` varchar(20) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `resolved_at` datetime(6) DEFAULT NULL,
  `device_id` bigint(20) DEFAULT NULL,
  `interface_id` bigint(20) DEFAULT NULL,
  `rule_id` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `alerts_device_id_7071e472_fk_devices_id` (`device_id`),
  KEY `alerts_interface_id_6d1acdf8_fk_interfaces_id` (`interface_id`),
  KEY `alerts_rule_id_fde026f4_fk_alert_rules_id` (`rule_id`),
  CONSTRAINT `alerts_device_id_7071e472_fk_devices_id` FOREIGN KEY (`device_id`) REFERENCES `devices` (`id`),
  CONSTRAINT `alerts_interface_id_6d1acdf8_fk_interfaces_id` FOREIGN KEY (`interface_id`) REFERENCES `interfaces` (`id`),
  CONSTRAINT `alerts_rule_id_fde026f4_fk_alert_rules_id` FOREIGN KEY (`rule_id`) REFERENCES `alert_rules` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla monitoreo_red.alerts: ~7 rows (aproximadamente)
REPLACE INTO `alerts` (`id`, `alert_type`, `severity`, `message`, `value_observed`, `threshold_value`, `status`, `created_at`, `resolved_at`, `device_id`, `interface_id`, `rule_id`) VALUES
	(1, 'device_down', 'critical', 'Caída del dispositivo (sin ICMP) - device_down RB Güigüe, Servidor desconectado', 0.0000, 0.0000, 'resuelta', '2026-10-06 01:06:39.939241', '2026-10-06 01:11:09.004269', 1, NULL, 1),
	(2, 'device_down', 'critical', 'Caída del dispositivo (sin ICMP) - device_down RB Güigüe, Servidor desconectado', 0.0000, 0.0000, 'resuelta', '2026-10-06 01:56:14.412587', '2026-10-06 01:57:37.887127', 1, NULL, 1),
	(3, 'device_down', 'critical', 'Caída del dispositivo (sin ICMP) - device_down RB Güigüe, Servidor desconectado', 0.0000, 0.0000, 'resuelta', '2026-10-06 03:22:10.059337', '2026-10-06 03:23:07.841732', 1, NULL, 1),
	(4, 'device_down', 'critical', 'Caída del dispositivo (sin ICMP) - device_down RB Güigüe, Servidor desconectado', 0.0000, 0.0000, 'resuelta', '2026-10-06 03:28:18.452719', '2026-10-06 03:28:40.387002', 1, NULL, 1),
	(5, 'device_down', 'critical', 'Caída del dispositivo (sin ICMP) RB Güigüe, Servidor desconectado', 0.0000, 0.0000, 'resuelta', '2026-10-06 21:33:03.924506', '2026-10-07 01:55:04.609314', 1, NULL, 1),
	(6, 'device_down', 'critical', 'Caída del dispositivo (sin ICMP) RB Güigüe, Servidor desconectado', 0.0000, 0.0000, 'resuelta', '2026-10-06 21:56:05.744436', '2026-10-07 01:54:53.565535', 1, NULL, 1),
	(7, 'device_down', 'critical', 'Caída del dispositivo (sin ICMP) RB Güigüe, Servidor desconectado', 0.0000, 0.0000, 'resuelta', '2026-10-06 22:09:54.190440', '2026-10-07 01:54:59.532387', 1, NULL, 1);

-- Volcando estructura para tabla monitoreo_red.auth_group
CREATE TABLE IF NOT EXISTS `auth_group` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla monitoreo_red.auth_group: ~2 rows (aproximadamente)
REPLACE INTO `auth_group` (`id`, `name`) VALUES
	(1, 'Administrador'),
	(2, 'Usuario');

-- Volcando estructura para tabla monitoreo_red.auth_group_permissions
CREATE TABLE IF NOT EXISTS `auth_group_permissions` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `group_id` int(11) NOT NULL,
  `permission_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla monitoreo_red.auth_group_permissions: ~0 rows (aproximadamente)

-- Volcando estructura para tabla monitoreo_red.auth_permission
CREATE TABLE IF NOT EXISTS `auth_permission` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `content_type_id` int(11) NOT NULL,
  `codename` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=61 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla monitoreo_red.auth_permission: ~60 rows (aproximadamente)
REPLACE INTO `auth_permission` (`id`, `name`, `content_type_id`, `codename`) VALUES
	(1, 'Can add log entry', 1, 'add_logentry'),
	(2, 'Can change log entry', 1, 'change_logentry'),
	(3, 'Can delete log entry', 1, 'delete_logentry'),
	(4, 'Can view log entry', 1, 'view_logentry'),
	(5, 'Can add permission', 2, 'add_permission'),
	(6, 'Can change permission', 2, 'change_permission'),
	(7, 'Can delete permission', 2, 'delete_permission'),
	(8, 'Can view permission', 2, 'view_permission'),
	(9, 'Can add group', 3, 'add_group'),
	(10, 'Can change group', 3, 'change_group'),
	(11, 'Can delete group', 3, 'delete_group'),
	(12, 'Can view group', 3, 'view_group'),
	(13, 'Can add user', 4, 'add_user'),
	(14, 'Can change user', 4, 'change_user'),
	(15, 'Can delete user', 4, 'delete_user'),
	(16, 'Can view user', 4, 'view_user'),
	(17, 'Can add content type', 5, 'add_contenttype'),
	(18, 'Can change content type', 5, 'change_contenttype'),
	(19, 'Can delete content type', 5, 'delete_contenttype'),
	(20, 'Can view content type', 5, 'view_contenttype'),
	(21, 'Can add session', 6, 'add_session'),
	(22, 'Can change session', 6, 'change_session'),
	(23, 'Can delete session', 6, 'delete_session'),
	(24, 'Can view session', 6, 'view_session'),
	(25, 'Can add Equipo', 7, 'add_device'),
	(26, 'Can change Equipo', 7, 'change_device'),
	(27, 'Can delete Equipo', 7, 'delete_device'),
	(28, 'Can view Equipo', 7, 'view_device'),
	(29, 'Can add Interfaz', 8, 'add_interface'),
	(30, 'Can change Interfaz', 8, 'change_interface'),
	(31, 'Can delete Interfaz', 8, 'delete_interface'),
	(32, 'Can view Interfaz', 8, 'view_interface'),
	(33, 'Can add Configuración del sistema', 9, 'add_systemconfig'),
	(34, 'Can change Configuración del sistema', 9, 'change_systemconfig'),
	(35, 'Can delete Configuración del sistema', 9, 'delete_systemconfig'),
	(36, 'Can view Configuración del sistema', 9, 'view_systemconfig'),
	(37, 'Can add Regla de alerta', 10, 'add_alertrule'),
	(38, 'Can change Regla de alerta', 10, 'change_alertrule'),
	(39, 'Can delete Regla de alerta', 10, 'delete_alertrule'),
	(40, 'Can view Regla de alerta', 10, 'view_alertrule'),
	(41, 'Can add Alerta', 11, 'add_alert'),
	(42, 'Can change Alerta', 11, 'change_alert'),
	(43, 'Can delete Alerta', 11, 'delete_alert'),
	(44, 'Can view Alerta', 11, 'view_alert'),
	(45, 'Can add Umbral (legacy)', 12, 'add_threshold'),
	(46, 'Can change Umbral (legacy)', 12, 'change_threshold'),
	(47, 'Can delete Umbral (legacy)', 12, 'delete_threshold'),
	(48, 'Can view Umbral (legacy)', 12, 'view_threshold'),
	(49, 'Can add Estado del Monitor', 13, 'add_monitorstatus'),
	(50, 'Can change Estado del Monitor', 13, 'change_monitorstatus'),
	(51, 'Can delete Estado del Monitor', 13, 'delete_monitorstatus'),
	(52, 'Can view Estado del Monitor', 13, 'view_monitorstatus'),
	(53, 'Can add Ejecución de Discovery', 14, 'add_discoveryjob'),
	(54, 'Can change Ejecución de Discovery', 14, 'change_discoveryjob'),
	(55, 'Can delete Ejecución de Discovery', 14, 'delete_discoveryjob'),
	(56, 'Can view Ejecución de Discovery', 14, 'view_discoveryjob'),
	(57, 'Can add Configuración del sistema', 15, 'add_systemconfig'),
	(58, 'Can change Configuración del sistema', 15, 'change_systemconfig'),
	(59, 'Can delete Configuración del sistema', 15, 'delete_systemconfig'),
	(60, 'Can view Configuración del sistema', 15, 'view_systemconfig');

-- Volcando estructura para tabla monitoreo_red.auth_user
CREATE TABLE IF NOT EXISTS `auth_user` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `password` varchar(128) NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `username` varchar(150) NOT NULL,
  `first_name` varchar(150) NOT NULL,
  `last_name` varchar(150) NOT NULL,
  `email` varchar(254) NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla monitoreo_red.auth_user: ~2 rows (aproximadamente)
REPLACE INTO `auth_user` (`id`, `password`, `last_login`, `is_superuser`, `username`, `first_name`, `last_name`, `email`, `is_staff`, `is_active`, `date_joined`) VALUES
	(1, 'pbkdf2_sha256$600000$4cZMtRQeCV5Vq69MrGX5eq$lLpVgWwmxi/55pTiQexJ1SZ1nq9y4dqfi1jasg4cLWg=', '2026-10-07 01:52:09.499156', 1, 'superuser', 'Victor', 'Fuenmayor', 'victormanuelfuenmayormn2@gmail.com', 1, 1, '2026-10-05 21:35:44.110935'),
	(2, 'pbkdf2_sha256$600000$Dam8Pa01eggdmtHJuX2J8p$QQo4rYPkFdUIkWImcNYbo0K6iUM+qliOwJ/jVz4/3ds=', NULL, 0, 'giscard', 'Giscard', 'Fuenmayor', '', 1, 1, '2026-10-07 00:29:47.040573');

-- Volcando estructura para tabla monitoreo_red.auth_user_groups
CREATE TABLE IF NOT EXISTS `auth_user_groups` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `group_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_groups_user_id_group_id_94350c0c_uniq` (`user_id`,`group_id`),
  KEY `auth_user_groups_group_id_97559544_fk_auth_group_id` (`group_id`),
  CONSTRAINT `auth_user_groups_group_id_97559544_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  CONSTRAINT `auth_user_groups_user_id_6a12ed8b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla monitoreo_red.auth_user_groups: ~1 rows (aproximadamente)
REPLACE INTO `auth_user_groups` (`id`, `user_id`, `group_id`) VALUES
	(1, 2, 1);

-- Volcando estructura para tabla monitoreo_red.auth_user_user_permissions
CREATE TABLE IF NOT EXISTS `auth_user_user_permissions` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `permission_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_user_permissions_user_id_permission_id_14a6b632_uniq` (`user_id`,`permission_id`),
  KEY `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla monitoreo_red.auth_user_user_permissions: ~0 rows (aproximadamente)

-- Volcando estructura para tabla monitoreo_red.devices
CREATE TABLE IF NOT EXISTS `devices` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `ip` varchar(45) NOT NULL,
  `device_type` varchar(50) NOT NULL,
  `device_role` varchar(20) NOT NULL,
  `vendor` varchar(50) DEFAULT NULL,
  `location` varchar(100) NOT NULL,
  `snmp_version` varchar(10) NOT NULL,
  `snmp_community` varchar(100) NOT NULL,
  `snmp_user` varchar(100) DEFAULT NULL,
  `snmp_auth` varchar(255) DEFAULT NULL,
  `snmp_priv` varchar(255) DEFAULT NULL,
  `tcp_ports` varchar(255) NOT NULL,
  `active` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ip` (`ip`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla monitoreo_red.devices: ~1 rows (aproximadamente)
REPLACE INTO `devices` (`id`, `name`, `ip`, `device_type`, `device_role`, `vendor`, `location`, `snmp_version`, `snmp_community`, `snmp_user`, `snmp_auth`, `snmp_priv`, `tcp_ports`, `active`, `created_at`, `updated_at`) VALUES
	(1, 'RB Güigüe', '10.253.215.3', 'router', 'core', 'mikrotik', 'Güigüe', '2c', 'public', NULL, NULL, NULL, '161', 1, '2026-10-05 21:44:29.884073', '2026-10-06 00:01:49.493689');

-- Volcando estructura para tabla monitoreo_red.discovery_jobs
CREATE TABLE IF NOT EXISTS `discovery_jobs` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `status` varchar(20) NOT NULL,
  `interfaces_found` int(11) NOT NULL,
  `interfaces_up` int(11) NOT NULL,
  `interfaces_created` int(11) NOT NULL,
  `interfaces_updated` int(11) NOT NULL,
  `interfaces_deleted` int(11) NOT NULL,
  `started_at` datetime(6) NOT NULL,
  `finished_at` datetime(6) DEFAULT NULL,
  `duration_ms` int(11) DEFAULT NULL,
  `error_message` longtext DEFAULT NULL,
  `device_id` bigint(20) NOT NULL,
  `triggered_by_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `discovery_jobs_device_id_7a89cd45_fk_devices_id` (`device_id`),
  KEY `discovery_jobs_triggered_by_id_9d708e17_fk_auth_user_id` (`triggered_by_id`),
  CONSTRAINT `discovery_jobs_device_id_7a89cd45_fk_devices_id` FOREIGN KEY (`device_id`) REFERENCES `devices` (`id`),
  CONSTRAINT `discovery_jobs_triggered_by_id_9d708e17_fk_auth_user_id` FOREIGN KEY (`triggered_by_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla monitoreo_red.discovery_jobs: ~4 rows (aproximadamente)
REPLACE INTO `discovery_jobs` (`id`, `status`, `interfaces_found`, `interfaces_up`, `interfaces_created`, `interfaces_updated`, `interfaces_deleted`, `started_at`, `finished_at`, `duration_ms`, `error_message`, `device_id`, `triggered_by_id`) VALUES
	(1, 'success', 20, 14, 20, 0, 0, '2026-10-05 21:44:44.346072', '2026-10-05 21:44:55.625048', 11064, NULL, 1, 1),
	(2, 'failed', 0, 0, 0, 0, 0, '2026-10-06 23:42:19.998602', '2026-10-06 23:43:24.276560', 64191, 'No se detectaron interfaces vía SNMP.', 1, 1),
	(3, 'success', 20, 14, 0, 20, 0, '2026-10-06 23:46:06.615765', '2026-10-06 23:46:17.507443', 10839, NULL, 1, 1),
	(4, 'success', 20, 14, 0, 20, 0, '2026-10-07 04:10:40.528979', '2026-10-07 04:11:18.626591', 38027, NULL, 1, 1);

-- Volcando estructura para tabla monitoreo_red.django_admin_log
CREATE TABLE IF NOT EXISTS `django_admin_log` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext DEFAULT NULL,
  `object_repr` varchar(200) NOT NULL,
  `action_flag` smallint(5) unsigned NOT NULL CHECK (`action_flag` >= 0),
  `change_message` longtext NOT NULL,
  `content_type_id` int(11) DEFAULT NULL,
  `user_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`),
  KEY `django_admin_log_user_id_c564eba6_fk_auth_user_id` (`user_id`),
  CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `django_admin_log_user_id_c564eba6_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla monitoreo_red.django_admin_log: ~0 rows (aproximadamente)

-- Volcando estructura para tabla monitoreo_red.django_content_type
CREATE TABLE IF NOT EXISTS `django_content_type` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) NOT NULL,
  `model` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla monitoreo_red.django_content_type: ~15 rows (aproximadamente)
REPLACE INTO `django_content_type` (`id`, `app_label`, `model`) VALUES
	(1, 'admin', 'logentry'),
	(2, 'auth', 'permission'),
	(3, 'auth', 'group'),
	(4, 'auth', 'user'),
	(5, 'contenttypes', 'contenttype'),
	(6, 'sessions', 'session'),
	(7, 'inventario', 'device'),
	(8, 'inventario', 'interface'),
	(9, 'alertas', 'systemconfig'),
	(10, 'alertas', 'alertrule'),
	(11, 'alertas', 'alert'),
	(12, 'alertas', 'threshold'),
	(13, 'monitoreo', 'monitorstatus'),
	(14, 'monitoreo', 'discoveryjob'),
	(15, 'core', 'systemconfig');

-- Volcando estructura para tabla monitoreo_red.django_migrations
CREATE TABLE IF NOT EXISTS `django_migrations` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `app` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=24 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla monitoreo_red.django_migrations: ~23 rows (aproximadamente)
REPLACE INTO `django_migrations` (`id`, `app`, `name`, `applied`) VALUES
	(1, 'contenttypes', '0001_initial', '2026-10-05 21:30:47.698394'),
	(2, 'auth', '0001_initial', '2026-10-05 21:31:38.727083'),
	(3, 'admin', '0001_initial', '2026-10-05 21:31:44.513702'),
	(4, 'admin', '0002_logentry_remove_auto_add', '2026-10-05 21:31:44.682204'),
	(5, 'admin', '0003_logentry_add_action_flag_choices', '2026-10-05 21:31:44.809778'),
	(6, 'inventario', '0001_initial', '2026-10-05 21:31:49.247673'),
	(7, 'alertas', '0001_initial', '2026-10-05 21:32:38.386173'),
	(8, 'contenttypes', '0002_remove_content_type_name', '2026-10-05 21:32:42.949902'),
	(9, 'auth', '0002_alter_permission_name_max_length', '2026-10-05 21:32:48.554838'),
	(10, 'auth', '0003_alter_user_email_max_length', '2026-10-05 21:32:49.396145'),
	(11, 'auth', '0004_alter_user_username_opts', '2026-10-05 21:32:49.528017'),
	(12, 'auth', '0005_alter_user_last_login_null', '2026-10-05 21:32:52.789742'),
	(13, 'auth', '0006_require_contenttypes_0002', '2026-10-05 21:32:52.912036'),
	(14, 'auth', '0007_alter_validators_add_error_messages', '2026-10-05 21:32:53.143061'),
	(15, 'auth', '0008_alter_user_username_max_length', '2026-10-05 21:32:54.053301'),
	(16, 'auth', '0009_alter_user_last_name_max_length', '2026-10-05 21:32:54.994639'),
	(17, 'auth', '0010_alter_group_name_max_length', '2026-10-05 21:32:55.834973'),
	(18, 'auth', '0011_update_proxy_permissions', '2026-10-05 21:32:55.966096'),
	(19, 'auth', '0012_alter_user_first_name_max_length', '2026-10-05 21:32:56.310667'),
	(20, 'monitoreo', '0001_initial', '2026-10-05 21:33:05.341112'),
	(21, 'sessions', '0001_initial', '2026-10-05 21:33:06.879640'),
	(22, 'alertas', '0002_alter_alertrule_metric_delete_systemconfig', '2026-10-05 22:42:32.150371'),
	(23, 'core', '0001_initial', '2026-10-05 22:42:35.136903');

-- Volcando estructura para tabla monitoreo_red.django_session
CREATE TABLE IF NOT EXISTS `django_session` (
  `session_key` varchar(40) NOT NULL,
  `session_data` longtext NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla monitoreo_red.django_session: ~2 rows (aproximadamente)
REPLACE INTO `django_session` (`session_key`, `session_data`, `expire_date`) VALUES
	('tllfvmpjndvkwlei6sevf2derc8xg7ga', '.eJxVjMsOwiAQRf-FtSHDo2Vw6d5vIAxMpWogKe3K-O_apAvd3nPOfYkQt7WErfMS5izOQonT70YxPbjuIN9jvTWZWl2XmeSuyIN2eW2Zn5fD_TsosZdvPQ2YNTsYMLFX6J0n7xKPdrIIoM1IltEAO0cWFKmoCXBCM2iTwSkt3h_I2za8:1xDqPo:yll1tI8hMB7KrE33vrE1Hbc749pUgq2NLvzEgBqHWOg', '2026-10-19 21:40:08.833192'),
	('w7hgymd6el0eaaovf1pt44lxy677a1mp', '.eJxVjMsOwiAQRf-FtSHDo2Vw6d5vIAxMpWogKe3K-O_apAvd3nPOfYkQt7WErfMS5izOQonT70YxPbjuIN9jvTWZWl2XmeSuyIN2eW2Zn5fD_TsosZdvPQ2YNTsYMLFX6J0n7xKPdrIIoM1IltEAO0cWFKmoCXBCM2iTwSkt3h_I2za8:1xEGpF:7cKdwaeHpYVlHGmofFm68GLVjm-SXdQJB_TI6V5hn3k', '2026-10-21 01:52:09.576990');

-- Volcando estructura para tabla monitoreo_red.interfaces
CREATE TABLE IF NOT EXISTS `interfaces` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `if_index` int(10) unsigned NOT NULL CHECK (`if_index` >= 0),
  `if_name` varchar(100) DEFAULT NULL,
  `if_alias` varchar(100) DEFAULT NULL,
  `if_speed_bps` bigint(20) DEFAULT NULL,
  `if_type` varchar(50) DEFAULT NULL,
  `admin_status` tinyint(1) NOT NULL,
  `oper_status` tinyint(1) NOT NULL,
  `monitored` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `device_id` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `interfaces_device_id_if_index_0dfbe99b_uniq` (`device_id`,`if_index`),
  CONSTRAINT `interfaces_device_id_c47c3c88_fk_devices_id` FOREIGN KEY (`device_id`) REFERENCES `devices` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=21 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla monitoreo_red.interfaces: ~20 rows (aproximadamente)
REPLACE INTO `interfaces` (`id`, `if_index`, `if_name`, `if_alias`, `if_speed_bps`, `if_type`, `admin_status`, `oper_status`, `monitored`, `created_at`, `device_id`) VALUES
	(1, 1, 'ether1', 'WAN', 1000000000, 'ethernet', 1, 1, 1, '2026-10-05 21:44:55.089713', 1),
	(2, 2, 'ether2', 'TROMPILLO- PINAL', 100000000, 'ethernet', 1, 1, 0, '2026-10-05 21:44:55.147146', 1),
	(3, 3, 'ether3', 'SECTORIAL GUIGUE', 100000000, 'ethernet', 1, 1, 0, '2026-10-05 21:44:55.151863', 1),
	(4, 4, 'ether4', 'TORRE COMFUTECH', 100000000, 'ethernet', 1, 1, 0, '2026-10-05 21:44:55.408605', 1),
	(5, 5, 'ether5', 'PORTACHUELO BELEN', 1000000000, 'ethernet', 1, 1, 0, '2026-10-05 21:44:55.412141', 1),
	(6, 6, 'ether6', '', 1000000000, 'ethernet', 0, 0, 0, '2026-10-05 21:44:55.421561', 1),
	(7, 7, 'ether7', '', 1000000000, 'ethernet', 0, 0, 0, '2026-10-05 21:44:55.423839', 1),
	(8, 8, 'ether8', 'SECTORIAL GUAICA TIAMITAS', 1000000000, 'ethernet', 0, 0, 0, '2026-10-05 21:44:55.426058', 1),
	(9, 9, 'ether9', 'ROUTER ABADIA', 1000000000, 'ethernet', 0, 0, 0, '2026-10-05 21:44:55.428999', 1),
	(10, 10, 'ether10', '', 1000000000, 'ethernet', 0, 0, 0, '2026-10-05 21:44:55.431147', 1),
	(11, 11, 'sfp-sfpplus1', '', 1000000000, 'ethernet', 1, 0, 0, '2026-10-05 21:44:55.433236', 1),
	(12, 13, 'local', '', 1000000000, 'type209', 1, 1, 0, '2026-10-05 21:44:55.435284', 1),
	(13, 17, '200_BELEN', '', 1000000000, 'l2vlan', 1, 1, 0, '2026-10-05 21:44:55.437413', 1),
	(14, 19, 'lo', '', 1000000000, 'type1', 1, 1, 0, '2026-10-05 21:44:55.439581', 1),
	(15, 20, 'wireguard1', '', 1000000000, 'type1', 1, 1, 0, '2026-10-05 21:44:55.441663', 1),
	(16, 22, 'WisphubVPN', 'WispHub VPN', 1000000000, 'type1', 1, 1, 0, '2026-10-05 21:44:55.444186', 1),
	(17, 23, 'back-to-home-vpn', 'back-to-home-vpn', 1000000000, 'type1', 1, 1, 0, '2026-10-05 21:44:55.446820', 1),
	(18, 24, '250_BELEN', '', 1000000000, 'l2vlan', 1, 1, 0, '2026-10-05 21:44:55.448959', 1),
	(19, 30, 'Trompillo_111', '', 100000000, 'l2vlan', 1, 1, 0, '2026-10-05 21:44:55.451084', 1),
	(20, 32, 'DAT-COM 215', '', 1000000000, 'l2vlan', 1, 1, 0, '2026-10-05 21:44:55.453161', 1);

-- Volcando estructura para tabla monitoreo_red.monitor_status
CREATE TABLE IF NOT EXISTS `monitor_status` (
  `id` smallint(5) unsigned NOT NULL CHECK (`id` >= 0),
  `last_heartbeat` datetime(6) NOT NULL,
  `status` varchar(20) NOT NULL,
  `hostname` varchar(100) NOT NULL,
  `pid` int(11) DEFAULT NULL,
  `last_traffic_run` datetime(6) DEFAULT NULL,
  `last_health_run` datetime(6) DEFAULT NULL,
  `last_icmp_run` datetime(6) DEFAULT NULL,
  `last_error` longtext DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla monitoreo_red.monitor_status: ~1 rows (aproximadamente)
REPLACE INTO `monitor_status` (`id`, `last_heartbeat`, `status`, `hostname`, `pid`, `last_traffic_run`, `last_health_run`, `last_icmp_run`, `last_error`) VALUES
	(1, '2026-10-07 02:03:24.126354', 'running', 'DESKTOP-35I0R1G', 13036, '2026-10-07 03:45:14.085157', '2026-10-07 03:44:49.644269', '2026-10-07 03:45:12.933788', NULL);

-- Volcando estructura para tabla monitoreo_red.system_config
CREATE TABLE IF NOT EXISTS `system_config` (
  `id` smallint(5) unsigned NOT NULL CHECK (`id` >= 0),
  `telegram_bot_token` varchar(255) NOT NULL,
  `telegram_chat_id` varchar(50) NOT NULL,
  `telegram_enabled` tinyint(1) NOT NULL,
  `influx_url` varchar(255) NOT NULL,
  `influx_token` varchar(500) NOT NULL,
  `influx_org` varchar(100) NOT NULL,
  `influx_bucket` varchar(100) NOT NULL,
  `grafana_url` varchar(500) NOT NULL,
  `monitor_enabled` tinyint(1) NOT NULL,
  `snmp_poll_interval` int(10) unsigned NOT NULL CHECK (`snmp_poll_interval` >= 0),
  `health_poll_interval` int(10) unsigned NOT NULL CHECK (`health_poll_interval` >= 0),
  `icmp_poll_interval` int(10) unsigned NOT NULL CHECK (`icmp_poll_interval` >= 0),
  `updated_at` datetime(6) NOT NULL,
  `updated_by_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `system_config_updated_by_id_e99ac947_fk_auth_user_id` (`updated_by_id`),
  CONSTRAINT `system_config_updated_by_id_e99ac947_fk_auth_user_id` FOREIGN KEY (`updated_by_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla monitoreo_red.system_config: ~1 rows (aproximadamente)
REPLACE INTO `system_config` (`id`, `telegram_bot_token`, `telegram_chat_id`, `telegram_enabled`, `influx_url`, `influx_token`, `influx_org`, `influx_bucket`, `grafana_url`, `monitor_enabled`, `snmp_poll_interval`, `health_poll_interval`, `icmp_poll_interval`, `updated_at`, `updated_by_id`) VALUES
	(1, '8631098212:AAGJvQr05xE7yW0POfRcv3dYEv-aT_xi0zQ', '-1004369073286', 1, 'http://192.168.0.248:8086', 'nuzc4-gtQtM8gHU2NMKCsS4chatcgH7ENG-vXTZ-wWv5E3II8TOrGPQpnLetYZVZhU_kySvCD5oADsjBk6CK9Q==', 'comfutech', 'metricas_red', 'http://192.168.0.248:3000', 1, 30, 60, 30, '2026-10-06 22:07:54.842149', 1);

-- Volcando estructura para tabla monitoreo_red.thresholds
CREATE TABLE IF NOT EXISTS `thresholds` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `metric` varchar(50) NOT NULL,
  `warning_value` decimal(20,4) DEFAULT NULL,
  `critical_value` decimal(20,4) DEFAULT NULL,
  `duration_sec` int(10) unsigned NOT NULL CHECK (`duration_sec` >= 0),
  `active` tinyint(1) NOT NULL,
  `device_id` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `thresholds_device_id_metric_5c522763_uniq` (`device_id`,`metric`),
  CONSTRAINT `thresholds_device_id_fb0ecec0_fk_devices_id` FOREIGN KEY (`device_id`) REFERENCES `devices` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla monitoreo_red.thresholds: ~0 rows (aproximadamente)

/*!40103 SET TIME_ZONE=IFNULL(@OLD_TIME_ZONE, 'system') */;
/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IFNULL(@OLD_FOREIGN_KEY_CHECKS, 1) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40111 SET SQL_NOTES=IFNULL(@OLD_SQL_NOTES, 1) */;
