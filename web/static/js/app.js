const { createApp } = Vue;

createApp({
    delimiters: ['[[', ']]'], // Change delimiters to avoid conflicts with Jinja2
    data() {
        return {
            currentView: 'dashboard',
            sidebarCollapsed: false,
            loading: false,
            projects: {},
            certifications: {},
            stats: {
                projects: {
                    total: 0,
                    completed: 0,
                    in_progress: 0,
                    not_started: 0
                },
                certifications: {
                    total: 0,
                    certified: 0,
                    ready_for_exam: 0,
                    in_progress: 0,
                    not_started: 0
                },
                study_sessions: {
                    total: 0
                }
            },
            projectFilters: {
                type: 'all',
                difficulty: ''
            },
            certFilters: {
                provider: 'all',
                difficulty: ''
            },
            toasts: [],
            toastId: 0
        };
    },
    computed: {
        viewTitle() {
            const titles = {
                dashboard: 'Dashboard',
                projects: 'Projetos',
                certifications: 'Certificações',
                progress: 'Progresso'
            };
            return titles[this.currentView] || 'Dashboard';
        },
        inProgressProjects() {
            return Object.entries(this.projects)
                .filter(([id, project]) => project.status === 'in_progress')
                .map(([id, project]) => ({
                    id,
                    ...project,
                    difficulty_stars: '⭐'.repeat(project.difficulty)
                }))
                .slice(0, 5);
        },
        inProgressCerts() {
            return Object.entries(this.certifications)
                .filter(([id, cert]) => cert.status === 'in_progress' || cert.status === 'ready_for_exam')
                .map(([id, cert]) => ({ id, ...cert }))
                .slice(0, 5);
        }
    },
    methods: {
        async loadProjects() {
            this.loading = true;
            try {
                const params = new URLSearchParams();
                if (this.projectFilters.type !== 'all') {
                    params.append('type', this.projectFilters.type);
                }
                if (this.projectFilters.difficulty) {
                    params.append('difficulty', this.projectFilters.difficulty);
                }

                const response = await axios.get(`/api/projects?${params.toString()}`);

                // Add difficulty_stars for display
                Object.keys(response.data).forEach(id => {
                    response.data[id].difficulty_stars = '⭐'.repeat(response.data[id].difficulty);
                });

                this.projects = response.data;
            } catch (error) {
                this.showToast('Erro ao carregar projetos', 'error');
                console.error(error);
            } finally {
                this.loading = false;
            }
        },
        async loadCertifications() {
            this.loading = true;
            try {
                const params = new URLSearchParams();
                if (this.certFilters.provider !== 'all') {
                    params.append('provider', this.certFilters.provider);
                }
                if (this.certFilters.difficulty) {
                    params.append('difficulty', this.certFilters.difficulty);
                }

                const response = await axios.get(`/api/certifications?${params.toString()}`);
                this.certifications = response.data;
            } catch (error) {
                this.showToast('Erro ao carregar certificações', 'error');
                console.error(error);
            } finally {
                this.loading = false;
            }
        },
        async loadProgress() {
            this.loading = true;
            try {
                const response = await axios.get('/api/progress');
                this.stats = response.data.stats;
            } catch (error) {
                this.showToast('Erro ao carregar progresso', 'error');
                console.error(error);
            } finally {
                this.loading = false;
            }
        },
        async startProject(projectId) {
            try {
                await axios.post(`/api/projects/${projectId}/start`);
                this.showToast('Projeto iniciado com sucesso!', 'success');
                await this.loadProjects();
                await this.loadProgress();
            } catch (error) {
                this.showToast('Erro ao iniciar projeto', 'error');
                console.error(error);
            }
        },
        async completeProject(projectId) {
            const notes = prompt('Adicionar notas sobre o projeto (opcional):');
            try {
                await axios.post(`/api/projects/${projectId}/complete`, {
                    status: 'completed',
                    notes: notes || undefined
                });
                this.showToast('Projeto concluído! 🎉', 'success');
                await this.loadProjects();
                await this.loadProgress();
            } catch (error) {
                this.showToast('Erro ao concluir projeto', 'error');
                console.error(error);
            }
        },
        async startCertification(certId) {
            const topic = prompt('Qual tópico você vai estudar? (opcional):');
            try {
                await axios.post(`/api/certifications/${certId}/start`, {
                    topic: topic || undefined
                });
                this.showToast('Sessão de estudo iniciada!', 'success');
                await this.loadCertifications();
                await this.loadProgress();
            } catch (error) {
                this.showToast('Erro ao iniciar certificação', 'error');
                console.error(error);
            }
        },
        async completeTopic(certId, topic) {
            try {
                await axios.post(`/api/certifications/${certId}/topic/${encodeURIComponent(topic)}`);
                this.showToast(`Tópico "${topic}" concluído!`, 'success');
                await this.loadCertifications();
                await this.loadProgress();
            } catch (error) {
                this.showToast('Erro ao completar tópico', 'error');
                console.error(error);
            }
        },
        async markCertified(certId) {
            const score = prompt('Digite seu score no exame (opcional):');
            const scoreInt = score ? parseInt(score) : undefined;

            if (score && (isNaN(scoreInt) || scoreInt < 0 || scoreInt > 100)) {
                this.showToast('Score inválido (deve ser entre 0 e 100)', 'error');
                return;
            }

            try {
                await axios.post(`/api/certifications/${certId}/certified`, {
                    score: scoreInt
                });
                this.showToast('Parabéns pela certificação! 🎓🎉', 'success');
                await this.loadCertifications();
                await this.loadProgress();
            } catch (error) {
                this.showToast('Erro ao marcar como certificado', 'error');
                console.error(error);
            }
        },
        async exportProgress() {
            try {
                const response = await axios.get('/api/progress');
                const dataStr = JSON.stringify(response.data.progress, null, 2);
                const dataBlob = new Blob([dataStr], { type: 'application/json' });
                const url = URL.createObjectURL(dataBlob);
                const link = document.createElement('a');
                link.href = url;
                link.download = `progress_${new Date().toISOString().slice(0, 10)}.json`;
                link.click();
                URL.revokeObjectURL(url);
                this.showToast('Progresso exportado com sucesso!', 'success');
            } catch (error) {
                this.showToast('Erro ao exportar progresso', 'error');
                console.error(error);
            }
        },
        async confirmReset() {
            if (!confirm('⚠️ ATENÇÃO!\n\nIsso irá apagar TODO o seu progresso de estudos.\nUm backup será criado automaticamente.\n\nTem certeza que deseja continuar?')) {
                return;
            }

            try {
                const response = await axios.delete('/api/progress/reset');
                this.showToast(`Progresso resetado. Backup: ${response.data.backup}`, 'info');
                await this.refreshData();
            } catch (error) {
                this.showToast('Erro ao resetar progresso', 'error');
                console.error(error);
            }
        },
        async refreshData() {
            await Promise.all([
                this.loadProjects(),
                this.loadCertifications(),
                this.loadProgress()
            ]);
        },
        viewProjectDetails(projectId) {
            // TODO: Implement project detail modal
            console.log('View project:', projectId);
        },
        showToast(message, type = 'info') {
            const icons = {
                success: 'fas fa-check-circle',
                error: 'fas fa-exclamation-circle',
                info: 'fas fa-info-circle',
                warning: 'fas fa-exclamation-triangle'
            };

            const toast = {
                id: this.toastId++,
                message,
                type,
                icon: icons[type] || icons.info
            };

            this.toasts.push(toast);

            // Auto-remove after 5 seconds
            setTimeout(() => {
                this.removeToast(toast.id);
            }, 5000);
        },
        removeToast(id) {
            const index = this.toasts.findIndex(t => t.id === id);
            if (index !== -1) {
                this.toasts.splice(index, 1);
            }
        }
    },
    watch: {
        currentView(newView) {
            // Load data when switching views
            if (newView === 'projects') {
                this.loadProjects();
            } else if (newView === 'certifications') {
                this.loadCertifications();
            } else if (newView === 'progress') {
                this.loadProgress();
            } else if (newView === 'dashboard') {
                this.refreshData();
            }
        }
    },
    mounted() {
        // Load initial data
        this.refreshData();

        // Setup keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + R: Refresh
            if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
                e.preventDefault();
                this.refreshData();
            }

            // Ctrl/Cmd + 1-4: Switch views
            if ((e.ctrlKey || e.metaKey) && e.key >= '1' && e.key <= '4') {
                e.preventDefault();
                const views = ['dashboard', 'projects', 'certifications', 'progress'];
                this.currentView = views[parseInt(e.key) - 1];
            }
        });

        console.log('🎓 Data Engineering Study Manager loaded!');
        console.log('💡 Keyboard shortcuts:');
        console.log('   Ctrl/Cmd + R: Refresh data');
        console.log('   Ctrl/Cmd + 1-4: Switch views');
    }
}).mount('#app');
