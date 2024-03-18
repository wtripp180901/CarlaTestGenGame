import pygame

class Game():
    def __init__(self):
        self.screen = pygame.display.set_mode((640,480))
        self._init_text()

    def _init_text(self):
        header_font = pygame.font.SysFont("ComicSans.tff",32)
        self.points_font = pygame.font.SysFont("ComicSans.tff",64)
        self.score_header_text = header_font.render("Test Points:",True,(255,0,0),None)
        self.score_header_rect = self.score_header_text.get_rect()
        self.score_text = self.points_font.render("0",True,(255,0,0),None)
        self.score_text_rect = self.score_text.get_rect()
        self.coverage_header_text = header_font.render("Coverage Points:",True,(255,0,0),None)
        self.coverage_header_rect = self.coverage_header_text.get_rect()
        self.coverage_text = self.points_font.render("0",True,(255,0,0),None)
        self.coverage_text_rect = self.coverage_text.get_rect()
        self.score_header_rect.center = (128,86)
        self.score_text_rect.center = (128,240)
        self.coverage_header_rect.center = (384,86)
        self.coverage_text_rect.center = (384,240)

    def update_score_text(self,test_points: str,coverage_points: str):
        self.score_text = self.points_font.render(test_points,True,(255,0,0),None)
        self.coverage_text = self.points_font.render(coverage_points,True,(255,0,0),None)

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
    
    def render(self):
        self.screen.fill((255,255,255))
        self.screen.blit(self.score_header_text,self.score_header_rect)
        self.screen.blit(self.coverage_header_text,self.coverage_header_rect)
        self.screen.blit(self.score_text,self.score_text_rect)
        self.screen.blit(self.coverage_text,self.coverage_text_rect)
        pygame.display.update()