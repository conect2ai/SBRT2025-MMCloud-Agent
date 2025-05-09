import numpy as np

def calculate_radar_area_original(data_area_radar):
    data_area_radar['rpm'] = data_area_radar['rpm']
    area_values = []

    for i in data_area_radar.itertuples():
        rpm = i.rpm / 100
        speed = i.speed
        throttle = i.throttle
        engine = i.engine_load

        values_normalized = [rpm, speed, throttle, engine]
        area = 0.5 * np.abs(np.dot(values_normalized, np.roll(values_normalized, 1)) * np.sin(2 * np.pi / len(values_normalized)))
        area_values.append(area)

    return area_values

class Cluster:
    def __init__(self, id, dimension):
        self.id = id
        self.dimension = dimension
        self.count = 0
        # self.sum = np.zeros(dimension)
        # self.sum_squares = np.zeros(dimension)
        self.mean = np.zeros(dimension)
        self.variance = np.zeros(dimension)
        self.cv = np.zeros(dimension)
        self.label = None  # Rótulo do cluster: 'cauteloso', 'normal', 'agressivo' ou None
    
    def add_point(self, point):
        point = np.array(point)
        self.count += 1
        old_mean = self.mean.copy()
        self.mean = old_mean + (point - old_mean) / self.count
        if self.count > 1:
            self.variance = ((self.count - 2) * self.variance + (point - old_mean) * (point - self.mean)) / (self.count - 1)
        else:
            self.variance = np.zeros(self.dimension)
        # Atualizar o CV
        self.cv = np.where(self.mean != 0, np.sqrt(self.variance) / self.mean, 0)
        # self.cv = np.where(
        #     np.asarray(self.mean) != 0, 
        #     np.sqrt(np.asarray(self.variance)) / np.asarray(self.mean), 
        #     0
        # )


class MMCloud:
    def __init__(self, dimension, max_clusters=3):
        self.dimension = dimension
        self.max_clusters = max_clusters
        self.clusters = []
        self.cluster_id_counter = 1
        # self.point_assignments = {}
        self.n_distances = 0  # Contador de distâncias processadas
        self.mean_distance = 0.0  # Média incremental
        self.variance_distance = 0.0  # Variância incremental
        # Inicializar o primeiro cluster
        initial_cluster = Cluster(self.cluster_id_counter, self.dimension)
        self.clusters.append(initial_cluster)
        self.cluster_id_counter += 1

    def update_mean_and_variance(self, new_distance):
        """Atualiza a média e a variância incrementalmente, sem guardar todas as distâncias"""
        self.n_distances += 1
        old_mean = self.mean_distance
        # Atualizar a média incremental
        self.mean_distance += (new_distance - self.mean_distance) / self.n_distances
        # Atualizar a variância incremental
        self.variance_distance += (new_distance - old_mean) * (new_distance - self.mean_distance)

    def calculate_dynamic_outlier_threshold(self):
        """Calcula o limiar de detecção de outliers com base na média e desvio padrão incremental"""
        if self.n_distances > 1:
            std_distance = (self.variance_distance / (self.n_distances - 1)) ** 0.5  # Desvio padrão
            return self.mean_distance + 2.67 * std_distance  # Limiar dinâmico
        else:
            return np.inf  # No início, não consideramos nenhum ponto como outlier

    def calculate_dynamic_dispersion_threshold(self):
        """Calcula o limiar de dispersão com base na média e desvio padrão incremental"""
        if self.n_distances > 1:
            std_distance = (self.variance_distance / (self.n_distances - 1)) ** 0.5  # Desvio padrão
            return self.mean_distance + 2.67 * std_distance  # Limiar dinâmico de dispersão
        else:
            return 1.0  # Valor inicial para garantir que algo seja retornado

    def split_cluster_with_variance(self, cluster):
        """Dividir o cluster usando a variância para identificar a direção de maior dispersão"""
        max_var_dimension = np.argmax(cluster.variance)

        mean_value = cluster.mean[max_var_dimension]
        variance_value = cluster.variance[max_var_dimension]

        cluster1 = Cluster(self.cluster_id_counter, self.dimension)
        cluster2 = Cluster(self.cluster_id_counter + 1, self.dimension)
        self.cluster_id_counter += 2

        cluster1.mean = cluster.mean.copy()
        cluster2.mean = cluster.mean.copy()

        cluster1.mean[max_var_dimension] = mean_value - 0.5 * variance_value
        cluster2.mean[max_var_dimension] = mean_value + 0.5 * variance_value

        cluster1.mean = np.where(cluster1.mean < 0, 0, cluster1.mean)
        cluster2.mean = np.where(cluster2.mean < 0, 0, cluster2.mean)

        return cluster1, cluster2

    def process_point(self, point_index, point):
        point = np.array(point)
        # Atribuir o ponto ao cluster mais próximo (baseado na distância euclidiana)
        min_distance = np.inf
        assigned_cluster = None
        for cluster in self.clusters:
            distance = np.linalg.norm(point - cluster.mean)
            if distance < min_distance:
                min_distance = distance
                assigned_cluster = cluster

        print(f"Min distance: {min_distance}")
        # Atualizar a média e variância incrementais com a nova distância
        self.update_mean_and_variance(min_distance)

        # Verificar se o ponto é um outlier com base no limiar dinâmico
        dynamic_outlier_threshold = self.calculate_dynamic_outlier_threshold()
        print(f"Dynamic outlier threshold: {dynamic_outlier_threshold}")

        if min_distance > dynamic_outlier_threshold and len(self.clusters) < self.max_clusters:
            print(f"Criando um novo cluster para o ponto {point_index}.")
            new_cluster = Cluster(self.cluster_id_counter, self.dimension)
            new_cluster.add_point(point)
            self.clusters.append(new_cluster)
            self.cluster_id_counter += 1
            # self.point_assignments[point_index] = (new_cluster.id, new_cluster.label)
        elif min_distance > dynamic_outlier_threshold:
            print(f"Ponto {point_index} foi identificado como outlier.")
            # self.point_assignments[point_index] = (-1, None)
        else:
            # Adicionar o ponto ao cluster atribuído
            assigned_cluster.add_point(point)
            # self.point_assignments[point_index] = (assigned_cluster.id, assigned_cluster.label)
            print(f"Ponto {point_index} atribuído ao cluster {assigned_cluster.id}")

        dispersion_threshold = self.calculate_dynamic_dispersion_threshold()
        if assigned_cluster.variance.sum() > dispersion_threshold and len(self.clusters) < self.max_clusters:
            cluster1, cluster2 = self.split_cluster_with_variance(assigned_cluster)
            self.clusters.remove(assigned_cluster)
            self.clusters.append(cluster1)
            self.clusters.append(cluster2)
            print(f"Cluster {assigned_cluster.id} foi dividido em {cluster1.id} e {cluster2.id}")

        self.update_label()

        return assigned_cluster.label
        # return assigned_cluster.id

    def get_outliers(self):
        """Retorna a lista de outliers identificados"""
        return self.outliers

    def update_label(self):
        if len(self.clusters) == 1:
            self.clusters[0].label = "normal"
        elif len(self.clusters) == 2:
            dist1 = np.linalg.norm(self.clusters[0].mean)
            dist2 = np.linalg.norm(self.clusters[1].mean)
            if dist1 < dist2:
                self.clusters[0].label = "cautious"
                self.clusters[1].label = "aggressive"
            else:
                self.clusters[0].label = "aggresive"
                self.clusters[1].label = "cautious"
        else:
            distances = [np.linalg.norm(cluster.mean) for cluster in self.clusters]
            cautious_index = np.argmin(distances)
            aggressive_index = np.argmax(distances)
            normal_index = 3 - cautious_index - aggressive_index

            self.clusters[cautious_index].label = 'cautious'
            self.clusters[aggressive_index].label = 'aggressive'
            self.clusters[normal_index].label = 'normal'

    def get_point_assignment(self, point_index):
        """Retorna a atribuição de cluster de um ponto específico"""
        return self.point_assignments.get(point_index, None)

    def get_clusters(self):
        """Retorna todos os clusters atuais"""
        return self.clusters